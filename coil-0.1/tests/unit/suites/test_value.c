COIL_TEST_SUITE(coil_value);

COIL_TEST_CASE(to_string)
{
  GValue  value = {0, };
  gchar  *string;
  GError *error = NULL;

  g_value_init(&value, G_TYPE_INT);
  g_value_set_int(&value, 100);

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "100");

  g_free(string);
  g_value_reset(&value);

  g_value_set_int(&value, -10);

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "-10");

  g_free(string);
  g_value_unset(&value);

  g_value_init(&value, G_TYPE_BOOLEAN);
  g_value_set_boolean(&value, TRUE);

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "True");

  g_free(string);
  g_value_reset(&value);

  g_value_set_boolean(&value, FALSE);

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "False");

  g_free(string);
  g_value_unset(&value);

  g_value_init(&value, G_TYPE_STRING);
  g_value_set_static_string(&value, "Hello World!");

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "'Hello World!'");

  g_free(string);
  g_value_unset(&value);

  g_value_init(&value, COIL_TYPE_NONE);
  g_value_set_object(&value, coil_none_object);

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "None");

  g_free(string);
  g_value_unset(&value);

  g_value_init(&value, COIL_TYPE_STRUCT);
  g_value_take_object(&value, coil_struct_new());

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "");

  g_free(string);

  g_value_reset(&value);

  g_value_take_object(&value, coil_parse_string("\n\
        a.b: 123\n\
        c: True\n\
        d: {}\n\
        e: -10\n\
        f: False\n\
        g: None\n\
        h: [1 2 True False 'Hi']\n\
  ", &error));
  g_assert_no_error(error);

  string = coil_value_to_string(&value, &error);

  g_assert_no_error(error);
  g_assert_cmpstr(string, ==, "a: {\n\
    b: 123\n\
}\n\
c: True\n\
d: {}\n\
e: -10\n\
f: False\n\
g: None\n\
h: [1 2 True False 'Hi']\n\
");

  g_free(string);
  g_value_unset(&value);
}

