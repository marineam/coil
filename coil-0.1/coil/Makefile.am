include $(top_srcdir)/Makefile.decl

AM_CPPFLAGS = $(GLIB_CFLAGS) $(GOBJECT_CFLAGS)

BUILT_SOURCES = 					\
				coil_parser.h 		\
				coil_parser.c 		\
				coil_scanner.c 		\
				coil_scanner.h		\
				coil_marshal.c		\
				coil_marshal.h

EXTRA_DIST +=			\
	coil_parser.h		\
	coil_scanner.h	\
	coil_marshal.h	\
	coil_marshal.list

lib_LTLIBRARIES = libcoil-@LIBCOIL_API_VERSION@.la

libcoil_@LIBCOIL_API_VERSION@_la_SOURCES = 			  \
				coil.c																		\
				coil_error.c															\
				coil_expandable.c 												\
				coil_include.c 														\
				coil_link.c 															\
				coil_list.c																\
				coil_marshal.c														\
				coil_none.c																\
				coil_parser.y															\
				coil_path.c	 															\
				coil_scanner.l														\
				coil_struct.c															\
				coil_value.c

libcoil_@LIBCOIL_API_VERSION@_la_LIBADD = @LEXLIB@ @GLIB_LIBS@
libcoil_@LIBCOIL_API_VERSION@_la_LDFLAG = -version-info $(LIBCOIL_SO_VERSION)

libcoil_includedir=$(includedir)/libcoil-$(LIBCOIL_API_VERSION)
libcoil_include_HEADERS=				\
				coil.h									\
				coil_error.h						\
				coil_expandable.h				\
				coil_include.h					\
				coil_link.h							\
				coil_list.h							\
				coil_marshal.h					\
				coil_none.h							\
				coil_parser.h						\
				coil_parser_extras.h		\
				coil_path.h							\
				coil_scanner.h 					\
				coil_struct.h						\
				coil_value.h

bin_PROGRAMS = coildebug
coildebug_SOURCES = coildebug.c
coildebug_LDADD = @GLIB_LIBS@ libcoil-@LIBCOIL_API_VERSION@.la

$(libcoil_la_OBJECTS): $(srcdir)/coil_parser.h

glib_genmarshal=`which glib-genmarshal`

coil_marshal.h: coil_marshal.list
	$(glib_genmarshal) --prefix=coil_cclosure_marshal $^ --header > $@

coil_marshal.c: coil_marshal.list
	$(glib_genmarshal) --prefix=coil_cclosure_marshal $^ --body > $@

coil_scanner.h: $(srcdir)/coil_scanner.l
	$(LEX) --header-file=$@ -o/dev/null $(srcdir)/coil_scanner.l

coil_scanner.c: $(srcdir)/coil_scanner.l
	$(LEX) -d -f -o $@ -i $(srcdir)/coil_scanner.l

coil_parser.h: $(srcdir)/coil_parser.c
coil_parser.c: $(srcdir)/coil_parser.y
	$(YACC) -t -v -d $(srcdir)/coil_parser.y -o $(srcdir)/coil_parser.c

clean-local:
	rm -f $(BUILT_SOURCES) coil_parser.output


