/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef COIL_STRUCT_H
#define COIL_STRUCT_H

#define COIL_TYPE_STRUCT              \
        (coil_struct_get_type())

#define COIL_STRUCT(obj)              \
        (G_TYPE_CHECK_INSTANCE_CAST((obj), COIL_TYPE_STRUCT, CoilStruct))

#define COIL_IS_STRUCT(obj)           \
        (G_TYPE_CHECK_INSTANCE_TYPE((obj), COIL_TYPE_STRUCT))

#define COIL_STRUCT_CLASS(klass)      \
        (G_TYPE_CHECK_CLASS_CAST((klass), COIL_TYPE_STRUCT, CoilStructClass))

#define COIL_IS_STRUCT_CLASS(klass)   \
        (G_TYPE_CHECK_CLASS_TYPE((klass), COIL_TYPE_STRUCT))

#define COIL_STRUCT_GET_CLASS(obj)    \
        (G_TYPE_INSTANCE_GET_CLASS((obj), COIL_TYPE_STRUCT, CoilStructClass))

#define coil_struct_new(args...) \
        g_object_new(COIL_TYPE_STRUCT, ## args, NULL)

struct _CoilStruct
{
  CoilExpandable     parent_instance;
  CoilStructPrivate *priv;

  // ** public **
  gchar         *doc;

  gboolean      always_expand : 1;
  gboolean      remember_deps : 1;
  gboolean      is_prototype : 1;
};

struct _CoilStructClass
{
  CoilExpandableClass parent_class;
};

struct _CoilStructIter
{
  const CoilStruct *node;
  GList            *position;
  guint             version;
};

typedef gboolean (*CoilStructFunc)(CoilStruct *, gpointer);

G_BEGIN_DECLS

GType
coil_struct_get_type (void) G_GNUC_CONST;

#ifdef COIL_DEBUG
void coil_struct_debug(CoilStruct *);
#endif

void
coil_struct_clear(CoilStruct *self);

gboolean
coil_struct_is_root(const CoilStruct *self);

gboolean
coil_struct_is_prototype(const CoilStruct *self);

gboolean
coil_struct_is_empty(const CoilStruct *self);

gboolean
coil_struct_is_ancestor(const CoilStruct *parent,
                        const CoilStruct *child);

gboolean
coil_struct_is_descendent(const CoilStruct *child,
                          const CoilStruct *parent);

CoilStruct *
coil_struct_get_root(const CoilStruct *self);

gboolean
coil_struct_has_same_root(const CoilStruct *a,
                          const CoilStruct *b);

const gchar *
coil_struct_get_path(const CoilStruct *self) G_GNUC_CONST;

void
coil_struct_set_path_value(CoilStruct *self,
                           gchar      *_path,
                           GValue     *value,
                           GError    **error);

void
coil_struct_set_key_value(CoilStruct    *self,
                          gchar         *key,
                          GValue        *value,
                          GError       **error);

gboolean
coil_struct_delete_path(CoilStruct   *self,
                        const gchar  *_path,
                        GError      **error);

gboolean
coil_struct_delete_key(CoilStruct  *self,
                       const gchar *key);

void
coil_struct_mark_path_deleted(CoilStruct  *self,
                              const gchar *_path,
                              CoilStruct **_container,
                              GError     **error);

void
coil_struct_mark_key_deleted(CoilStruct  *self,
                             gchar       *key,
                             GError     **error);

gboolean
coil_struct_is_deleted_key(const CoilStruct  *self,
                           const gchar *key);

gboolean
coil_struct_is_deleted_path(const CoilStruct *self,
                            const gchar *path);

gboolean
coil_struct_has_dependency(CoilStruct *self,
                      GType       type,
                      gpointer    object);

void
coil_struct_add_dependency(CoilStruct *self,
                           GType       type,
                           gpointer    object);

void
coil_struct_extend_path(CoilStruct   *self,
                        const gchar  *_path,
                        GError      **error);

void
coil_struct_extend(CoilStruct         *self,
                   CoilStruct         *parent,
                   GError            **error);

void
coil_struct_iter_init(CoilStructIter *iter,
                      const CoilStruct *node);

gboolean
coil_struct_iter_next(CoilStructIter *iter,
                      gchar          **key,
                      gchar          **path,
                      GValue         **value);

void
coil_struct_merge(CoilStruct  *src,
                  CoilStruct  *dest,
                  gboolean     overwrite,
                  GError     **error);

gboolean
coil_struct_expand_recursive(CoilStruct  *self,
                             GError     **error);

gboolean
coil_struct_expand(CoilStruct *self,
                   GError    **error);

GValue *
coil_struct_get_key_value(CoilStruct  *self,
                     const gchar      *key,
                     gboolean          expand_value,
                     GError          **error);

GValue *
coil_struct_get_path_value(CoilStruct  *self,
                           const gchar *path,
                           gboolean     expand_value,
                           GError     **error);

gboolean
coil_struct_contains_key(CoilStruct   *self,
                         const gchar  *key,
                         gboolean      check_secondary_keys);

gboolean
coil_struct_contains_path(CoilStruct   *self,
                          const gchar  *path,
                          gboolean      check_secondary_keys);

GList *
coil_struct_get_keys(CoilStruct *self);

GList *
coil_struct_get_paths(CoilStruct *self);

GList *
coil_struct_get_values(CoilStruct *self);

guint
coil_struct_get_size(const CoilStruct *self);

void
coil_struct_build_string(CoilStruct *self,
                         GString    *const buffer,
                         GError    **error);

gchar *
coil_struct_to_string(CoilStruct *self,
                      GError    **error);

CoilStruct *
coil_struct_copy(CoilStruct       *self,
                 const CoilStruct *new_container,
                 GError          **error);

gboolean
coil_struct_equals(gconstpointer e1,
                   gconstpointer e2,
                   GError        **error);

void
coil_struct_foreach_container(CoilStruct     *self,
                              CoilStructFunc  func,
                              gpointer        user_data);

G_END_DECLS

#endif
