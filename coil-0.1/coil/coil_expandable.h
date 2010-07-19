/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef COIL_EXPANDABLE_H
#define COIL_EXPANDABLE_H


#define COIL_TYPE_EXPANDABLE          \
        (coil_expandable_get_type())

#define COIL_EXPANDABLE(obj)          \
        (G_TYPE_CHECK_INSTANCE_CAST((obj), COIL_TYPE_EXPANDABLE, \
          CoilExpandable))

#define COIL_IS_EXPANDABLE(obj)       \
        (G_TYPE_CHECK_INSTANCE_TYPE((obj), COIL_TYPE_EXPANDABLE))

#define COIL_EXPANDABLE_CLASS(klass)  \
        (G_TYPE_CHECK_CLASS_CAST((klass), COIL_TYPE_EXPANDABLE, \
          CoilExpandableClass))

#define COIL_IS_EXPANDABLE_CLASS(klass) \
        (G_TYPE_CHECK_CLASS_TYPE((klass), COIL_TYPE_EXPANDABLE))

#define COIL_EXPANDABLE_GET_CLASS(obj)  \
        (G_TYPE_INSTANCE_GET_CLASS((obj), COIL_TYPE_EXPANDABLE, \
          CoilExpandableClass))

#define coil_expandable_error_new(code, exp, format, args...)         \
        coil_error_new(code, (COIL_EXPANDABLE(exp))->location,        \
                        format, ## args)

#define coil_expandable_error_new_literal(code, exp, message)         \
        coil_error_new_literal(code,                                  \
                                (COIL_EXPANDABLE(exp))->location,     \
                                message)

struct _CoilExpandable
{
  GObject                parent_instance;
  CoilExpandablePrivate *priv;

  // ** public **
  CoilLocation location;
  CoilStruct *container;
};

struct _CoilExpandableClass
{
  GObjectClass parent_class;

  /* Abstract Methods */
  gboolean (*expand) (CoilExpandable *self,
                      GHashTable     *visited,
                      GError        **error);

  gint (*equals) (gconstpointer   e1,
                  gconstpointer   e2,
                  GError        **error);

  void  (*build_string) (CoilExpandable *self,
                         GString        *const buffer,
                         GError        **error);
};

G_BEGIN_DECLS

GType
coil_expandable_get_type(void) G_GNUC_CONST;

gboolean
coil_expand_value_internal(GValue     *value,
                           GValue    **real_value,
                           GHashTable *visited,
                           GError    **error);

gboolean
coil_expand_value(GValue      *value,
                  GValue     **real_value,
                  GError     **error);

gboolean
coil_expand(gpointer     obj,
            GHashTable  *visited,
            GError     **error);

gboolean
coil_is_expanded(gconstpointer obj);

gboolean
coil_expandable_equals(gconstpointer  e1,
                       gconstpointer  e2,
                       GError       **error);

gboolean
coil_expandable_value_equals(const GValue  *v1,
                             const GValue  *v2,
                             GError       **error);

void
coil_expandable_build_string(CoilExpandable *self,
                             GString        *const buffer,
                             GError        **error);

gchar *
coil_expandable_to_string(CoilExpandable  *self,
                          GError         **error);

G_END_DECLS

#endif /* COIL_EXPANDABLE_H */
