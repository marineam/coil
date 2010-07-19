/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef COIL_H
#define COIL_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>

#ifdef HAVE_CONFIG_H
#  include "config.h"
#endif

#ifndef COIL_DEBUG
#  define G_DISABLE_CHECKS 1
#endif

#include "glib.h"
#include "glib-object.h"

#define MAX_INCLUDE_DEPTH 10

#define COIL_API(rtype) rtype

#define COIL_STATIC_STRLEN(str) str,(sizeof(str)-1)

#define COIL_SPECIAL_CHAR '@'
#define COIL_SPECIAL_CHAR_S "@"

/* block padding chars for string output */
#define COIL_BLOCK_PADDING "    " /* 4 spaces */
#define COIL_BLOCK_PADDING_LEN                                      \
  (COIL_STATIC_STRLEN(COIL_BLOCK_PADDING))

/* character to quote single line strings */
#define COIL_STRING_QUOTE '\''
/* string escape character */
#define COIL_STRING_ESCAPE '\\'
/* multiline quote string */
#define COIL_MULTILINE_QUOTE_S "'''"
/* multiline quotes after line exceeds n chars */
#define COIL_MULTILINE_LEN 80

#define COIL_STRING_EXPAND_REGEX \
        "\\$\\{[\\w][\\w\\d\\-\\_]*(\\.[\\w][\\w\\d\\-\\_]*)*\\}"

#define COIL_TYPE_LOCATION (coil_location_get_type())

/* filename:first_line.first_col-last_line.last_col */
#define COIL_LOCATION_FORMAT "line %d in %s "
#define COIL_LOCATION_FORMAT_ARGS(loc)                            \
        (loc).first_line, (loc).filepath
/*
        (loc).first_line, (loc).first_column,
        (loc).last_line, (loc).last_column
*/

#define _COIL_NOT_IMPLEMENTED_ACTION                              \
    g_error("%s:%s Not implemented.",                             \
            G_STRFUNC,                                            \
            G_STRLOC);                                            \
    g_assert_not_reached();                                       \

#define COIL_NOT_IMPLEMENTED(rtype)                               \
  G_STMT_START                                                    \
  {                                                               \
    _COIL_NOT_IMPLEMENTED_ACTION                                  \
    return (rtype);                                               \
  }                                                               \
  G_STMT_END

#define COIL_NOT_IMPLEMENTED_VOID                                 \
  G_STMT_START                                                    \
  {                                                               \
    _COIL_NOT_IMPLEMENTED_ACTION                                  \
  }                                                               \
  G_STMT_END

typedef struct _CoilStruct        CoilStruct;
typedef struct _CoilStructClass   CoilStructClass;
typedef struct _CoilStructPrivate CoilStructPrivate;
typedef struct _CoilStructIter    CoilStructIter;

typedef struct _CoilExpandable         CoilExpandable;
typedef struct _CoilExpandableClass    CoilExpandableClass;
typedef struct _CoilExpandablePrivate  CoilExpandablePrivate;

typedef struct _CoilLocation
{
  guint first_line;
  guint first_column;
  guint last_line;
  guint last_column;
  const gchar *filepath;
} CoilLocation;

G_BEGIN_DECLS

void
coil_init(void);

GType
coil_location_get_type(void) G_GNUC_CONST;

guint
coil_str_hash(gconstpointer p);

G_END_DECLS

#include "coil_error.h"
#include "coil_list.h"
#include "coil_path.h"
#include "coil_expandable.h"
#include "coil_link.h"
#include "coil_include.h"
#include "coil_struct.h"
#include "coil_value.h"
#include "coil_none.h"
#include "coil_parser_extras.h"
#include "coil_marshal.h"

#endif
