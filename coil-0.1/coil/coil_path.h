/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef _COIL_PATH_H
#define _COIL_PATH_H

typedef enum
{
  COIL_PATH_KEY       = (1 << 0),
  COIL_PATH_CONTAINER = (1 << 1),
  COIL_PATH_ABSOLUTE  = (1 << 2),
  COIL_PATH_RELATIVE  = (1 << 3),
  COIL_PATH           = (1 << 2 | 1 << 3)
} CoilPathType;

#define COIL_ROOT_PATH \
        COIL_SPECIAL_CHAR_S "root"

#define COIL_ROOT_PATH_LEN \
        (sizeof(COIL_ROOT_PATH)-1)

#define COIL_PATH_DELIM '.'
#define COIL_PATH_DELIM_S "."

#define COIL_PATH_IS_RELATIVE(path)                           \
        (strncmp((path), COIL_ROOT_PATH, COIL_ROOT_PATH_LEN))

#define COIL_PATH_IS_ABSOLUTE(path)                           \
        (!COIL_PATH_IS_RELATIVE((path)))

#define COIL_PATH_IS_ROOT(path)                               \
        (!strcmp((path), COIL_ROOT_PATH))

#define COIL_PATH_IS_KEY(path)                                \
        (*(path) != COIL_SPECIAL_CHAR &&                      \
         NULL == strchr((path), COIL_PATH_DELIM))

#define COIL_PATH_IS_REFERENCE(path)                          \
        ((*(path) == COIL_PATH_DELIM))

#define COIL_KEY_REGEX "-*[a-zA-Z_][\\w-]*"

#define COIL_PATH_REGEX                                       \
        "(" COIL_SPECIAL_CHAR_S "|\\.\\.+)?"                  \
        COIL_KEY_REGEX "(\\." COIL_KEY_REGEX ")*"

#define COIL_PATH_LEN 255
#define COIL_PATH_BUFLEN (COIL_PATH_LEN + 1) /* +1 for '\0' */

G_BEGIN_DECLS


gchar *
coil_path_build(const gchar *base, ...) G_GNUC_NULL_TERMINATED
                                        G_GNUC_WARN_UNUSED_RESULT;

void
coil_path_build_buffer(gpointer buffer,
                       gchar *base, ...) G_GNUC_NULL_TERMINATED;

gchar *
coil_path_get_container(const gchar *path) G_GNUC_WARN_UNUSED_RESULT;

gchar *
coil_path_get_key(const gchar *path) G_GNUC_WARN_UNUSED_RESULT;

gboolean
coil_validate_path(const gchar *path);

gboolean
coil_validate_key(const gchar *key);

gboolean
coil_path_resolve_full(const gchar *base,
                       const gchar *reference,
                       gchar       *path,
                       gchar       *container,
                       gchar       *key,
                       GError     **error);

gboolean
coil_path_resolve(const gchar *base,
                  const gchar *reference,
                  gchar       *path,
                  GError     **error);

gchar *
coil_path_relativize(const gchar *base,
                     const gchar *path) G_GNUC_WARN_UNUSED_RESULT;

gboolean
coil_path_is_descendent(const gchar *path,
                        const gchar *container_path);

gboolean
coil_path_has_container(const gchar *path,
                        const gchar *maybe_container);

G_END_DECLS
#endif

