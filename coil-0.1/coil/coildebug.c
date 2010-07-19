/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

static const char *stdin_name = "(stdin)";

int main(int argc, char **argv)
{
  CoilStruct *root = NULL;
  GError     *error = NULL;

  coil_init();

  if (argc > 1)
  {
    int      i;
    GString *buffer = g_string_sized_new(8192);

    for (i = 1; i < argc; i++)
    {
      if (!g_file_test(argv[i], G_FILE_TEST_EXISTS |
                                G_FILE_TEST_IS_REGULAR))
          g_error("Error: file '%s' does not exist.", argv[i]);
      else
        root = coil_parse_file(argv[i], &error);

      if (G_UNLIKELY(error))
        goto fail;

      coil_struct_build_string(root, buffer, &error);

      if (G_UNLIKELY(error))
        goto fail;

      g_print("%s", buffer->str);

      g_string_truncate(buffer, 0);
      g_object_unref(root);
      root = NULL;
    }

    g_string_free(buffer, TRUE);
  }
  else
  {
    root = coil_parse_stream(stdin, stdin_name, &error);

    if (G_UNLIKELY(error))
      goto fail;

    g_object_unref(root);
    root = NULL;
  }

  return 0;

fail:
  if (root != NULL && G_IS_OBJECT(root))
    g_object_unref(root);

  g_assert(error != NULL);
  g_printerr("Error: %s\n", error->message);

  return 0;
}

