COIL_TEST_SUITE(coil_path);

#define _BEGIN(desc)                          \
        if (strlen((desc)))                   \
          g_test_message("+%s\n", (desc))

#define _END

COIL_TEST_CASE(MACROS)
{
  g_assert(COIL_PATH_IS_ROOT("@root"));
  g_assert(!COIL_PATH_IS_ROOT("something"));

  g_assert(COIL_PATH_IS_ABSOLUTE("@root.some.path"));
  g_assert(!COIL_PATH_IS_ABSOLUTE("some.path"));

  g_assert(COIL_PATH_IS_RELATIVE("some.relative.path"));
  g_assert(!COIL_PATH_IS_RELATIVE("@root.some.absolute.path"));
}

COIL_TEST_CASE(build)
{
  gchar *result;

  result = coil_path_build("@root", "one", "two", "three", NULL);
  g_assert_cmpstr(result, ==, "@root.one.two.three");
  g_free(result);

  result = coil_path_build("this", "is", "a", "relative_path", NULL);
  g_assert_cmpstr(result, ==, "this.is.a.relative_path");
  g_free(result);

  result = NULL;
}

COIL_TEST_CASE(build_buffer)
{
  gchar buffer[COIL_PATH_BUFLEN];

  coil_path_build_buffer(&buffer, "@root", "one", "two", "three", NULL);
  g_assert_cmpstr(buffer, ==, "@root.one.two.three");

  bzero(&buffer, sizeof(buffer));
  coil_path_build_buffer(&buffer, "some", "relative", "path", NULL);
  g_assert_cmpstr(buffer, ==, "some.relative.path");
}

COIL_TEST_CASE(get_container)
{
  gchar *container;

  container = coil_path_get_container("@root.some.random.coil.container.key");
  g_assert_cmpstr(container, ==, "@root.some.random.coil.container");
  g_free(container);

  container = coil_path_get_container("some.relative.container.key");
  g_assert_cmpstr(container, ==, "some.relative.container");
  g_free(container);

  container = coil_path_get_container("some_key");
  g_assert(!container);

  container = coil_path_get_container("");
  g_assert(!container);
}

COIL_TEST_CASE(get_key)
{
  gchar *key;

  key = coil_path_get_key("@root.some.container.with.key");
  g_assert_cmpstr(key, ==, "key");
  g_free(key);

  key = coil_path_get_key("some.container.with.a.key");
  g_assert_cmpstr(key, ==, "key");
  g_free(key);

  key = coil_path_get_key("some_key");
  g_assert_cmpstr(key, ==, "some_key");
  g_free(key);
}

COIL_TEST_CASE(validate_path)
{
 /*
  * XXX: as of 3/29/10 - Contains all pyCoil test cases.
  */
  g_assert(coil_validate_path("foo"));
  g_assert(coil_validate_path("foo.bar"));
  g_assert(coil_validate_path("@root"));
  g_assert(!coil_validate_path("#blah"));

  g_assert(coil_validate_path("@root.more-.-complex-._path_"));
  g_assert(coil_validate_path(".......a.b.c.d.-e-._f"));
  g_assert(coil_validate_path("a.b.c.d.e.f.g"));

  g_assert(!coil_validate_path("@root.a..b"));
  g_assert(!coil_validate_path("..a..b.c"));
}

COIL_TEST_CASE(validate_key)
{
  /*
   * XXX: as of 3/29/10 - Contains all pyCoil test cases.
   */
  g_assert(coil_validate_key("foo"));
  g_assert(!coil_validate_key("foo.bar"));
  g_assert(!coil_validate_key("@root"));
  g_assert(!coil_validate_key("#blah"));

  g_assert(!coil_validate_key("@anything"));
  g_assert(!coil_validate_key("..something"));
  /* XXX: we could probably allow numbers?? */
  g_assert(!coil_validate_key("0123asdf"));

}

COIL_TEST_CASE(resolve_full)
{

#define BEGIN(desc) _BEGIN((desc));                           \
        {                                                     \
          GError *error                      = NULL;          \
          gchar path[COIL_PATH_BUFLEN]      = {0, };         \
          gchar container[COIL_PATH_BUFLEN] = {0, };         \
          gchar key[COIL_PATH_BUFLEN]       = {0, };         \

#define END _END                                              \
          if (error != NULL)                                  \
          {                                                   \
            g_error_free(error);                              \
            error = NULL;                                     \
          }                                                   \
        }

  BEGIN("Test basic append, no back references");
    {
      coil_path_resolve_full("@root.a.b.c", "d.e.f",
                            path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.a.b.c.d.e.f");
      g_assert_cmpstr(container, ==, "@root.a.b.c.d.e");
      g_assert_cmpstr(key, ==, "f");
    }
  END;

  BEGIN("Test basic append 2");
    {
      coil_path_resolve_full("@root.one.two.three", "four.five",
                            path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.one.two.three.four.five");
      g_assert_cmpstr(container, ==, "@root.one.two.three.four");
      g_assert_cmpstr(key, ==, "five");
    }
  END;

  BEGIN("Append to @root only.");
    {
      coil_path_resolve_full("@root", "a",
                             path, container, key, &error);
      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.a");
      g_assert_cmpstr(container, ==, "@root");
      g_assert_cmpstr(key, ==, "a");
    }
  END;

  BEGIN("Test one back reference");
    {
      coil_path_resolve_full("@root.one.two.three", "..three",
                              path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.one.two.three");
      g_assert_cmpstr(container, ==, "@root.one.two");
      g_assert_cmpstr(key, ==, "three");
    }
  END;

  BEGIN("Test reference to root and from root");
    {
      coil_path_resolve_full("@root.one.two.three", "....xxx.yyy.zzz",
                            path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.xxx.yyy.zzz");
      g_assert_cmpstr(container, ==, "@root.xxx.yyy");
      g_assert_cmpstr(key, ==, "zzz");
    }
  END;

  BEGIN("Test root reference");
    {
      coil_path_resolve_full("@root.doesnt.matter", "@root",
                            path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root");
      g_assert_cmpstr(container, ==, "@root");
      g_assert_cmpstr(key, ==, "");
    }
  END;

  BEGIN("Test absolute path reference");
    {
      coil_path_resolve_full("@root.doesnt.matter", "@root.container.key",
                              path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.container.key");
      g_assert_cmpstr(container, ==, "@root.container");
      g_assert_cmpstr(key, ==, "key");
    }
  END;

  BEGIN("Test absolute with a bunch of keys.");
    {
      coil_path_resolve_full("@root.some.ignored.path",
                             "@root.some.other.path.with.a.lot.of.keys",
                             path, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "@root.some.other.path.with.a.lot.of.keys");
      g_assert_cmpstr(container, ==, "@root.some.other.path.with.a.lot.of");
      g_assert_cmpstr(key, ==, "keys");
    }
  END;

  BEGIN("Test alloca with internal buffer instead of ours");
    {
      coil_path_resolve_full("@root.some.path", "..container.key",
                              NULL, container, key, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, "");
      g_assert_cmpstr(container, ==, "@root.some.container");
      g_assert_cmpstr(key, ==, "key");
    }
  END;

  BEGIN("container buffer as NULL");
    {
        coil_path_resolve_full("@root.some.path", "..container.key",
                                path, NULL, key, &error);

        g_assert_no_error(error);
        g_assert_cmpstr(path, ==, "@root.some.container.key");
        g_assert_cmpstr(container, ==, "");
        g_assert_cmpstr(key, ==, "key");
    }
  END;

  /*
   * Error conditions
   */

  BEGIN("Test reference past root error");
    {
      coil_path_resolve_full("@root", "..oh.no.reference.past.root",
                            path, NULL, NULL, &error);

      g_assert_error(error, COIL_ERROR, COIL_ERROR_PATH);
    }
  END;

  BEGIN("Test invalid absolute path error");
    {
      coil_path_resolve_full("@root.something", "@rootasfd",
                            path, NULL, NULL, &error);

      g_assert_error(error, COIL_ERROR, COIL_ERROR_PATH);
    }
  END;

  BEGIN("Test mid path reference error");
    {
      coil_path_resolve_full("@root.some.path", "..some.mid.path..reference",
                            path, NULL, NULL, &error);

      g_assert_error(error, COIL_ERROR, COIL_ERROR_PATH);
    }
  END;

  BEGIN("Test long paths");
    {
      const gchar long_path[COIL_PATH_BUFLEN + 1] =
              "@root."                    /* 6 + ... */
              "ech.row.has.twntyfve.chr." /* 10 Rows of 25 chars */
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr."
              "ech.row.has.twntyfve.chr";

      g_assert(strlen(long_path) == COIL_PATH_LEN);

      coil_path_resolve_full(long_path, "..chr",
                            path, NULL, NULL, &error);

      g_assert_no_error(error);
      g_assert_cmpstr(path, ==, long_path);

      BEGIN("Test too long path is invalid");
        {
          /* should be 1 too large */
          coil_path_resolve_full(long_path, "..chrs",
                                path, NULL, NULL, &error);

          g_assert_error(error, COIL_ERROR, COIL_ERROR_PATH);
        }
      END;

    }
  END;

  BEGIN("Test backreference with no key error");
    {

      coil_path_resolve_full("@root.some.path", "..",
                            path, NULL, NULL, &error);

      g_assert_error(error, COIL_ERROR, COIL_ERROR_PATH);
    }
  END;

#undef BEGIN
#undef END
}

COIL_TEST_CASE(relativize)
{
#define BEGIN(desc) _BEGIN((desc)); { \
         gchar *result = NULL;
#define END _END g_free(result); }

  BEGIN("Path is longer");
    {
      result = coil_path_relativize("@root.asdf.bxd",
                                    "@root.asdf.bhd.xxx.yyy");
      g_assert_cmpstr(result, ==, "..bhd.xxx.yyy");
    }
  END;

  BEGIN("Base is longer");
    {
      result = coil_path_relativize("@root.asdf.bxd.xxx.yyy",
                                    "@root.asdf.bhd");
      g_assert_cmpstr(result, ==, "....bhd");
    }
  END;

  BEGIN("Path is longer, base is key-complete prefix of path");
    {
      result = coil_path_relativize("@root.asdf.bhd",
                                    "@root.asdf.bhd.xyz");
      g_assert_cmpstr(result, ==, "xyz");
    }
  END;

  BEGIN("Base is longer, path is key-complete prefix of base");
    {
      result = coil_path_relativize("@root.asdf.bhd.xyz",
                                    "@root.asdf.bhd");
      g_assert_cmpstr(result, ==, "...bhd");
    }
  END;

  BEGIN("base == path");
    {
      result = coil_path_relativize("@root.asdf.asdf",
                                    "@root.asdf.asdf");
      g_assert_cmpstr(result, ==, "..asdf");
    }
  END;

  BEGIN("Relative to nothing");
    {
      result = coil_path_relativize(NULL, "this.is.a.cool.path");
      g_assert_cmpstr(result, ==, "this.is.a.cool.path");
    }
  END;

  BEGIN("Path is already relative");
    {
      result = coil_path_relativize("some.random.path",
                                    "..hi.my.name.is.john");
      g_assert_cmpstr(result, ==, "..hi.my.name.is.john");
    }
  END;

#undef BEGIN
#undef END
}

COIL_TEST_CASE(is_descendent)
{
#define BEGIN(desc) _BEGIN((desc)); {\
         gboolean result;
#define END _END }

  BEGIN("Basic TRUE cases")
  {
    result = coil_path_is_descendent("@root.a.b.c.d", "@root.a.b.c");
    g_assert(result);

    result = coil_path_is_descendent("@root.a.b.c.d", "@root.a.b");
    g_assert(result);

    result = coil_path_is_descendent("@root.a.b.c.d", "@root.a");
    g_assert(result);

    result = coil_path_is_descendent("@root.a.b.c.d", "@root");
    g_assert(result);

    result = coil_path_is_descendent(
        "@root.some_container.key", "@root.some_container");
    g_assert(result);

    result = coil_path_is_descendent(
        "@root.some.longer.path.with.a.lot.of.keys.to.look.through",
        "@root.some.longer.path.with.a.lot.of.keys.to.look");
    g_assert(result);
  }
  END;

  BEGIN("Basic FALSE cases")
  {
    result = coil_path_is_descendent(
      "@root.abc.def.ghi.jkl.mno",
      "@root.abc.def.ghi.jkl.mno");
    g_assert(!result);

    result = coil_path_is_descendent(
      "@root.abc.def.ghi.jkl.mno",
      "@root.abc.def.ghi.XXX");
    g_assert(!result);

    result = coil_path_is_descendent(
      "@root.xxx_some.key",
      "@root.xxx_another.key");
    g_assert(!result);

    result = coil_path_is_descendent("@root", "@root");
    g_assert(!result);
  }
  END;

#undef BEGIN
#undef END
}
