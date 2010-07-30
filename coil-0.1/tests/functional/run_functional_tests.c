#include "coil.h"

#define TEST_CASES_PATH "./cases/"
#define TEST_FILE_PREFIX "test_"
#define TEST_FILE_SUFFIX ".coil"
#define TEST_KEY_NAME "test"
#define TEST_PASS_STR "pass"
#define TEST_FAIL_STR "fail"
#define EXPECTED_KEY_NAME "expected"

static void run_test(gconstpointer arg);

static GSList *
read_test_dir(const gchar *dirpath)
{
  GDir         *dir;
  GError       *error = NULL;
  GSList       *entries = NULL;
  const gchar  *entry;

  dir = g_dir_open(dirpath, 0, &error);
  g_assert_no_error(error);

  while ((entry = g_dir_read_name(dir)) != NULL)
  {
    gchar *fullpath = g_build_filename(dirpath, entry, NULL);

    if (g_file_test(fullpath, G_FILE_TEST_IS_DIR))
      entries = g_slist_concat(entries, read_test_dir(fullpath));
    else if (g_str_has_prefix(entry, TEST_FILE_PREFIX)
      && g_str_has_suffix(entry, TEST_FILE_SUFFIX)
      && g_file_test(fullpath, G_FILE_TEST_IS_REGULAR))
    {
      entries = g_slist_prepend(entries, fullpath);
      continue;
    }

    g_free(fullpath);
  }

  g_dir_close(dir);

  return entries;
}

static void
build_functional_test_suite(void)
{
  gchar                  test_name[FILENAME_MAX];
  gint                   num_cases;
  GSList                *cases;
  register const GSList *lp;
  register gchar        *np;

  cases = read_test_dir(TEST_CASES_PATH);

  for (lp = cases;
       lp != NULL;
       lp = g_slist_next(lp), num_cases++)
  {
    np = test_name;
    memcpy(np, (gchar *)lp->data + 1, FILENAME_MAX);
    np = strrchr(np, '.');
    *np = '\0';

    g_test_add_data_func(test_name, (gchar *)lp->data, run_test);
  }

  if (!num_cases)
    g_error("No test cases found in %s", TEST_CASES_PATH);

  g_slist_free(cases);
}

static void
expect_common(const gchar *filepath, GError **ret_error)
{
  CoilStruct *root;
  GError     *error = NULL;
  GValue     *test, *expected;

  root = coil_parse_file(filepath, &error);
  if (error) goto done;

  test = coil_struct_get_key_value(root, TEST_KEY_NAME, FALSE, &error);
  if (error) goto done;

  expected = coil_struct_get_key_value(root, EXPECTED_KEY_NAME, FALSE, &error);
  if (error) goto done;

  if (test == NULL ^ expected == NULL)
  {
    if (test == NULL)
      g_error("Must specify 'test' if 'expected' is set.");

    if (expected == NULL)
      g_error("Must specify 'expected' if 'test' is set.");
  }

  /* expand everything to catch expand errors in syntax */
  coil_struct_expand_recursive(root, &error);
  if (error) goto done;

  if (test == NULL ^ expected == NULL)
  {
    const gint result = coil_value_compare(test, expected, &error);
    if (error) goto done;

    if (result != 0)
    {
      gchar *string = coil_struct_to_string(root, &error);
      g_set_error(&error, COIL_ERROR, COIL_ERROR_INTERNAL,
                  "Failed: \n\n%s\n", string);
      g_free(string);
      goto done;
    }
  }

done:
  if (root)
    g_object_unref(root);

  if (error)
      g_propagate_error(ret_error, error);
}

static void
expect_pass(const gchar *filepath)
{
  GError     *error = NULL;

  expect_common(filepath, &error);
  g_assert_no_error(error);
}

static void
expect_fail(const gchar *filepath)
{
  GError     *error = NULL;

  expect_common(filepath, &error);
  g_assert(error != NULL);
}

static void
run_test(const void *arg)
{
  gchar *filepath = (gchar *)arg;
  const guint offset = sizeof(TEST_CASES_PATH)-1;

  if (strncmp(filepath + offset,
              TEST_PASS_STR,
              sizeof(TEST_PASS_STR) - 1) == 0)
  {
    expect_pass(filepath);
  }
  else if (strncmp(filepath + offset,
                    TEST_FAIL_STR,
                    sizeof(TEST_FAIL_STR) - 1) == 0)
  {
    expect_fail(filepath);
  }

  g_free(filepath);
}

int main(int argc, char **argv)
{
  g_type_init();
  g_test_init(&argc, &argv, NULL);

  build_functional_test_suite();

  return g_test_run();
}

