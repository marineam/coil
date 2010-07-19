COIL_TEST_SUITE(coil_struct);

static CoilStruct *a = NULL, *b = NULL, *c = NULL;
static CoilStruct *x = NULL, *y = NULL, *z = NULL;
static GValue *v1, *v2, *v3;
static GError *error = NULL;

static void setup(void)
{
  error = NULL;
  x = NULL;
  y = NULL;
  z = NULL;
  v1 = NULL;
  v2 = NULL;
  v3 = NULL;

  a = coil_parse_string("             \
    a: {                              \
      b: { x:1 y:2 z:3 }              \
    }", &error);

  g_assert(error == NULL);

  b = coil_parse_string("             \
    a.b.x: 1                          \
    a.b.y: 2                          \
    a.b.z: 3                          \
    ", &error);

  g_assert(error == NULL);

  c = coil_parse_string("             \
    x: {                              \
      x:1                             \
      y:2                             \
      z:3                             \
    }                                 \
    y: { x:1 y:2 z:3 }                \
    z: { x:1 }                        \
    z.y: 2                            \
    z.z: 3                            \
    ", &error);

  g_assert(error == NULL);

  g_assert(COIL_IS_STRUCT(a));
  g_assert(COIL_IS_STRUCT(b));
}

static void teardown(void)
{
  if (a)
    g_object_unref(a);
  a = NULL;

  if (b)
    g_object_unref(b);
  b = NULL;

  if (c)
    g_object_unref(c);
  c = NULL;
}

COIL_TEST_CASE(equals)
{
  setup();

  g_assert(coil_struct_equals(a, a, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(b, b, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(c, c, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(a, b, &error));
  g_assert_no_error(error);
  g_assert(!coil_struct_equals(a, c, &error));
  g_assert_no_error(error);
  g_assert(!coil_struct_equals(b, c, &error));
  g_assert_no_error(error);

  v1 = coil_struct_get_key_value(c, "x", TRUE, &error);
  g_assert_no_error(error);

  v2 = coil_struct_get_key_value(c, "y", TRUE, &error);
  g_assert_no_error(error);

  x = COIL_STRUCT(g_value_get_object(v1));
  y = COIL_STRUCT(g_value_get_object(v2));

  v3 = coil_struct_get_path_value(x, "..z", TRUE, &error);
  z = COIL_STRUCT(g_value_get_object(v3));

  g_assert(coil_struct_equals(x, x, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(z, z, &error));
  g_assert_no_error(error);

  g_assert(coil_struct_equals(x, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, z, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(z, x, &error));
  g_assert_no_error(error);

  g_assert(!coil_struct_equals(x, a, &error));
  g_assert_no_error(error);
  g_assert(!coil_struct_equals(y, a, &error));
  g_assert_no_error(error);
  g_assert(!coil_struct_equals(z, a, &error));
  g_assert_no_error(error);

  coil_struct_clear(a);
  coil_struct_clear(b);
  coil_struct_clear(c);

  g_assert(coil_struct_equals(a, a, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(b, b, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(c, c, &error));
  g_assert_no_error(error);

  g_assert(coil_struct_equals(a, b, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(b, c, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(c, a, &error));
  g_assert_no_error(error);

  teardown();
}

COIL_TEST_CASE(extend_basic)
{
  a = coil_parse_string("           \
    a: { x:1 y:2 z:3 }              \
    b: { @extends: ..a }            \
  ", &error);
  g_assert_no_error(error);
  g_assert(COIL_IS_STRUCT(a));

  v1 = coil_struct_get_key_value(a, "a", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v1, COIL_TYPE_STRUCT));
  x = COIL_STRUCT(g_value_get_object(v1));

  v2 = coil_struct_get_key_value(a, "b", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v2, COIL_TYPE_STRUCT));
  y = COIL_STRUCT(g_value_get_object(v2));

  g_assert(coil_struct_equals(x, x, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(x, y, &error));
  g_assert_no_error(error);
  g_assert(!coil_struct_equals(a, x, &error));
  g_assert_no_error(error);


  b = coil_parse_string("                   \
    a.b: { a: 'Hello World' x: 1 y:2 z:3 }  \
    x: { @extends: ..a w:0 }                \
    y: { @extends: ..a }                    \
    y.w: 0                                  \
    z: { w: 0 @extends: ..a }               \
  ", &error);
  g_assert_no_error(error);
  g_assert(COIL_IS_STRUCT(b));

  v1 = coil_struct_get_key_value(b, "x", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v1, COIL_TYPE_STRUCT));
  x = COIL_STRUCT(g_value_get_object(v1));

  v2 = coil_struct_get_key_value(b, "y", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v2, COIL_TYPE_STRUCT));
  y = COIL_STRUCT(g_value_get_object(v2));

  v3 = coil_struct_get_key_value(b, "z", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v3, COIL_TYPE_STRUCT));
  z = COIL_STRUCT(g_value_get_object(v3));

  g_assert(coil_struct_equals(x, x, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(z, z, &error));
  g_assert_no_error(error);

  g_assert(coil_struct_equals(x, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, z, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(z, x, &error));
  g_assert_no_error(error);

  g_object_unref(a);
  g_object_unref(b);
}

COIL_TEST_CASE(mark_deleted_keys)
{
  a = coil_parse_string("                         \
    a.b: { a: 'Hello World' x:1 y:2 z:3 }         \
    x: { @extends: ..a ~b.a b.w:0 }               \
    y: { ~b.a b.w:0 @extends: ..a }               \
    z.b: { w:0 x:1 y:2 z:3 }                      \
  ", &error);

  g_assert_no_error(error);
  g_assert(COIL_IS_STRUCT(a));

  v1 = coil_struct_get_key_value(a, "x", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v1, COIL_TYPE_STRUCT));
  x = COIL_STRUCT(g_value_get_object(v1));

  v2 = coil_struct_get_key_value(a, "y", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v2, COIL_TYPE_STRUCT));
  y = COIL_STRUCT(g_value_get_object(v2));

  v3 = coil_struct_get_key_value(a, "z", FALSE, &error);
  g_assert_no_error(error);
  g_assert(G_VALUE_HOLDS(v3, COIL_TYPE_STRUCT));
  z = COIL_STRUCT(g_value_get_object(v3));

  g_assert(coil_struct_equals(x, x, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(z, z, &error));
  g_assert_no_error(error);

  g_assert(coil_struct_equals(x, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(y, z, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(z, x, &error));
  g_assert_no_error(error);

  g_object_unref(a);
}

COIL_TEST_CASE(clear)
{
  setup();

  g_assert(!coil_struct_equals(a, c, &error));
  g_assert_no_error(error);

  coil_struct_clear(a);
  coil_struct_clear(c);

  g_assert(coil_struct_equals(a, c, &error));
  g_assert_no_error(error);

  teardown();
}

COIL_TEST_CASE(is_root)
{
  setup();

  g_assert(coil_struct_is_root(a));
  v1 = coil_struct_get_path_value(a, "a.b", TRUE, &error);
  g_assert_no_error(error);
  x = COIL_STRUCT(g_value_get_object(v1));
  g_assert(!coil_struct_is_root(x));

  teardown();
}

COIL_TEST_CASE(is_ancestor)
{
  setup();

  v1 = coil_struct_get_path_value(a, "a.b", TRUE, &error);
  g_assert_no_error(error);
  x = COIL_STRUCT(g_value_get_object(v1));

  g_assert(coil_struct_is_ancestor(a, x));
  g_assert(!coil_struct_is_ancestor(x, a));

  g_assert(coil_struct_is_descendent(x, a));
  g_assert(!coil_struct_is_descendent(a, x));

  teardown();
}

COIL_TEST_CASE(get_root)
{
  setup();

  v1 = coil_struct_get_path_value(a, "a.b", TRUE, &error);
  g_assert_no_error(error);
  x = COIL_STRUCT(g_value_get_object(v1));

  g_assert(coil_struct_get_root(x) == a);
  g_assert(coil_struct_get_root(x) != b);

  teardown();
}

COIL_TEST_CASE(delete_key)
{
  setup();

  x = coil_struct_new();

  g_assert(coil_struct_delete_key(a, "a"));

  g_assert(coil_struct_equals(a, x, &error));
  g_assert_no_error(error);

  v1 = coil_struct_get_path_value(b, "a.b", TRUE, &error);
  g_assert_no_error(error);
  g_assert(v1);
  y = COIL_STRUCT(g_value_get_object(v1));

  g_assert(coil_struct_delete_key(y, "x"));
  g_assert(!coil_struct_delete_key(y, "x"));

  g_assert(coil_struct_delete_key(y, "y"));
  g_assert(coil_struct_delete_key(y, "z"));

  g_assert(coil_struct_equals(a, y, &error));
  g_assert_no_error(error);

  g_assert(coil_struct_equals(x, y, &error));
  g_assert_no_error(error);

  g_object_unref(x);

  teardown();
}

COIL_TEST_CASE(delete_path)
{
  setup();

  coil_struct_delete_path(a, "a.b.x", &error);
  g_assert_no_error(error);

  v1 = coil_struct_get_path_value(a, "a.b", TRUE, &error);
  g_assert_no_error(error);
  g_assert(v1);

  x = COIL_STRUCT(g_value_get_object(v1));
  v1 = coil_struct_get_key_value(x, "x", TRUE, &error);
  g_assert_no_error(error);
  g_assert(v1 == NULL);

  v1 = coil_struct_get_key_value(x, "y", TRUE, &error);
  g_assert_no_error(error);
  g_assert(v1);
  g_assert(G_VALUE_HOLDS(v1, G_TYPE_INT));
  g_assert(g_value_get_int(v1) == 2);

  v1 = coil_struct_get_key_value(x, "z", TRUE, &error);
  g_assert_no_error(error);
  g_assert(v1);
  g_assert(G_VALUE_HOLDS(v1, G_TYPE_INT));
  g_assert(g_value_get_int(v1) == 3);

  g_assert(coil_struct_delete_path(a, "a.b.y", &error));
  g_assert_no_error(error);

  g_assert(coil_struct_delete_path(a, "a.b.z", &error));
  g_assert_no_error(error);

  g_assert(coil_struct_delete_path(a, "a", &error));
  g_assert_no_error(error);

  g_assert(!coil_struct_delete_path(a, "a", &error));
  g_assert_no_error(error);

  g_assert(coil_struct_delete_path(b, "a", &error));
  g_assert_no_error(error);

  g_assert(coil_struct_equals(a, b, &error));
  g_assert_no_error(error);

  y = coil_struct_new();
  g_assert(coil_struct_equals(a, y, &error));
  g_assert_no_error(error);
  g_assert(coil_struct_equals(b, y, &error));
  g_assert_no_error(error);

  g_object_unref(y);

  teardown();
}

COIL_TEST_CASE(get_size)
{
  setup();

  x = coil_parse_string("                         \
    a: { x:True y:False z:42 }                    \
    b: { @extends: ..a c: 123 }                   \
  ", &error);
  g_assert_no_error(error);

  g_assert_cmpuint(coil_struct_get_size(a), ==, 1);
  g_assert_cmpuint(coil_struct_get_size(b), ==, 1);
  g_assert_cmpuint(coil_struct_get_size(c), ==, 3);
  g_assert_cmpuint(coil_struct_get_size(x), ==, 2);

  v1 = coil_struct_get_key_value(x, "a", FALSE, &error);
  g_assert_no_error(error);
  g_assert(v1 != NULL);
  g_assert(G_VALUE_HOLDS(v1, COIL_TYPE_STRUCT));
  y = COIL_STRUCT(g_value_get_object(v1));

  v2 = coil_struct_get_key_value(x, "b", FALSE, &error);
  g_assert_no_error(error);
  g_assert(v2 != NULL);
  g_assert(G_VALUE_HOLDS(v2, COIL_TYPE_STRUCT));
  z = COIL_STRUCT(g_value_get_object(v2));

  g_assert(!coil_is_expanded(z));
  g_assert_cmpuint(coil_struct_get_size(y), ==, 3);
  g_assert_cmpuint(coil_struct_get_size(z), ==, 4);
  g_assert(!coil_is_expanded(z));

  g_object_unref(x);

  teardown();
}

COIL_TEST_CASE(has_same_root)
{
  setup();

  g_assert(!coil_struct_has_same_root(a, b));
  g_assert(!coil_struct_has_same_root(b, c));
  g_assert(!coil_struct_has_same_root(a, c));

  g_assert(coil_struct_has_same_root(a, a));

  v1 = coil_struct_get_path_value(a, "a", TRUE, &error);
  g_assert_no_error(error);

  x = COIL_STRUCT(g_value_get_object(v1));

  v2 = coil_struct_get_path_value(a, "a.b", TRUE, &error);
  g_assert_no_error(error);

  y = COIL_STRUCT(g_value_get_object(v2));

  g_assert(coil_struct_has_same_root(x, y));
  g_assert(coil_struct_has_same_root(y, x));

  v3 = coil_struct_get_path_value(b, "a", TRUE, &error);
  g_assert_no_error(error);

  z = COIL_STRUCT(g_value_get_object(v3));

  g_assert(!coil_struct_has_same_root(x, z));
  g_assert(!coil_struct_has_same_root(z, y));

  teardown();
}
