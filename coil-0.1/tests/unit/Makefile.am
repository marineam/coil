include $(top_srcdir)/Makefile.decl

AM_COLOR_TESTS=always
AM_CPPFLAGS = $(GLIB_CFLAGS) -I$(top_srcdir)/coil -g

EXTRA_DIST+=suites

test%.c: generate_suite.awk
	test ! -f "suites/$@" ||	$(AWK) -f generate_suite.awk suites/$@ > $(srcdir)/$@

noinst_PROGRAMS = $(TEST_PROGS)
dist_noinst_SCRIPTS = generate_suite.awk
TEST_PROGS += test_path
test_path_SOURCES = test_path.c
test_path_LDADD = $(test_libs)

TEST_PROGS += test_struct
test_struct_SOURCES = test_struct.c
test_struct_LDADD = $(test_libs)

TEST_PROGS += test_value
test_value_SOURCES = test_value.c
test_value_LDADD = $(test_libs)

clean-local:
	rm -f $(srcdir)/test_*.c

CLEANFILES = $(GTESTER_LOG)

