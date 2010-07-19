/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef _COIL_ERROR_H
#define _COIL_ERROR_H

typedef enum
{
  COIL_ERROR_FILE,
  COIL_ERROR_INTERNAL,
  COIL_ERROR_KEY,
  COIL_ERROR_KEY_MISSING,
  COIL_ERROR_LINK,
  COIL_ERROR_PARSE,
  COIL_ERROR_PATH,
  COIL_ERROR_STRUCT,
  COIL_ERROR_VALUE,
} CoilError;

#define COIL_ERROR coil_error_quark()

#define coil_error_new(code, location, format, args...)           \
        g_error_new(COIL_ERROR,                                   \
                    (code),                                       \
                    COIL_LOCATION_FORMAT format,                  \
                    COIL_LOCATION_FORMAT_ARGS(location),          \
                    ##args)

#define coil_error_new_literal(code, location, message)           \
        g_error_new(COIL_ERROR,                                   \
                    (code),                                       \
                    COIL_LOCATION_FORMAT "%s",                    \
                    COIL_LOCATION_FORMAT_ARGS(location),          \
                    message)

#define coil_set_error(err, code, location, format, args...)      \
        g_set_error((err),                                        \
                    COIL_ERROR,                                   \
                    (code),                                       \
                    COIL_LOCATION_FORMAT format,                  \
                    COIL_LOCATION_FORMAT_ARGS(location),          \
                    ##args)

#define coil_set_error_literal(err, code, location, message)      \
        g_set_error_literal((err),                                \
                            COIL_ERROR,                           \
                            (code),                               \
                            COIL_LOCATION_FORMAT "%s",            \
                            message)

#define coil_expandable_set_error(err, code, ex, format, args...) \
        coil_set_error(err, code,                                 \
                      COIL_EXPANDABLE(ex)->location,              \
                       format, ##args)

#define coil_struct_set_error(err, st, format, args...)           \
        coil_expandable_set_error(err, COIL_ERROR_STRUCT,         \
                        st, "(in struct) " format, ##args)

#define coil_link_set_error(err, link, format, args...)           \
        coil_expandable_set_error(err, COIL_ERROR_LINK,           \
                        link, format, ##args)

#define coil_error_matches(err, code)                             \
        g_error_matches(err, COIL_ERROR, (code))


#define coil_propagate_error g_propagate_error
#define coil_propagate_prefixed_error g_propagate_prefixed_error

G_BEGIN_DECLS

GQuark
coil_error_quark(void);

G_END_DECLS

#endif

