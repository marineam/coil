/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

G_DEFINE_ABSTRACT_TYPE(CoilExpandable, coil_expandable, G_TYPE_OBJECT);

#define COIL_EXPANDABLE_GET_PRIVATE(obj) \
  (G_TYPE_INSTANCE_GET_PRIVATE((obj), COIL_TYPE_EXPANDABLE, \
                               CoilExpandablePrivate))

struct _CoilExpandablePrivate
{
  gboolean expanded : 1;
  GValue  *real_value;
};

typedef enum {
  PROP_O,
  PROP_CONTAINER,
  PROP_EXPANDED,
  PROP_LOCATION,
  PROP_REAL_VALUE,
} CoilExpandableProperties;

static void
coil_expandable_set_property(GObject      *object,
                             guint         property_id,
                             const GValue *value,
                             GParamSpec   *pspec)
{
  CoilExpandable        *self;
  CoilExpandablePrivate *priv;

  self = COIL_EXPANDABLE(object);
  priv = self->priv;

  switch (property_id)
  {
    case PROP_CONTAINER:
      self->container = g_value_get_object(value);
      break;

    case PROP_EXPANDED:
      priv->expanded = g_value_get_boolean(value);
      break;

    case PROP_LOCATION:
    {
      if (self->location.filepath)
        g_free(self->location.filepath);

      CoilLocation *loc_ptr;
      loc_ptr = (CoilLocation *)g_value_get_pointer(value);
      if (loc_ptr)
      {
        self->location = *((CoilLocation *)loc_ptr);
        self->location.filepath = g_strdup(loc_ptr->filepath);
      }
      break;
    }

    case PROP_REAL_VALUE:
    {
      GValue *val_ptr;
      if (priv->real_value)
        free_value(priv->real_value);

      val_ptr = (GValue *)g_value_get_pointer(value);
      if (val_ptr)
        priv->real_value = copy_value(val_ptr);
      break;
    }

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
      break;
  }
}

static void
coil_expandable_get_property(GObject    *object,
                             guint       property_id,
                             GValue     *value,
                             GParamSpec *pspec)
{
  CoilExpandable        *self;
  CoilExpandablePrivate *priv;

  self = COIL_EXPANDABLE(object);
  priv = self->priv;

  switch (property_id)
  {
    case PROP_CONTAINER:
      g_value_set_object(value, self->container);
      break;

    case PROP_EXPANDED:
      g_value_set_boolean(value, priv->expanded);
      break;

    case PROP_LOCATION:
      g_value_set_pointer(value, &(self->location));
      break;

    case PROP_REAL_VALUE:
      g_value_set_pointer(value, priv->real_value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
      break;
  }
}

static void
coil_expandable_init(CoilExpandable *self)
{
  CoilExpandablePrivate *priv;

  g_return_if_fail(COIL_IS_EXPANDABLE(self));

  priv             = COIL_EXPANDABLE_GET_PRIVATE(self);

  self->priv       = priv;
  self->container  = NULL;

  memset(&self->location, 0, sizeof(CoilLocation));

  priv->expanded   = FALSE;
  priv->real_value = NULL;
}

static void
coil_expandable_finalize(GObject *object)
{
  CoilExpandable        *self;
  CoilExpandablePrivate *priv;

  self = COIL_EXPANDABLE(object);
  priv = self->priv;

  if (priv->real_value)
    free_value(priv->real_value);
}

COIL_API(void)
coil_expandable_build_string(CoilExpandable *self,
                             GString        *const buffer,
                             GError        **error)
{
  CoilExpandableClass *klass;

  g_return_if_fail(COIL_IS_EXPANDABLE(self));
  g_return_if_fail(error == NULL || *error == NULL);

  klass = COIL_EXPANDABLE_GET_CLASS(self);

  g_return_if_fail(klass->build_string != NULL);

  return klass->build_string(self, buffer, error);
}

COIL_API(gchar *)
coil_expandable_to_string(CoilExpandable *self,
                          GError        **error)
{
  g_return_val_if_fail(COIL_IS_EXPANDABLE(self), NULL);
  g_return_val_if_fail(error == NULL || *error == NULL, NULL);

  GString *buffer = g_string_sized_new(128);
  coil_expandable_build_string(self, buffer, error);

  return g_string_free(buffer, FALSE);
}

static void
coil_expandable_class_init(CoilExpandableClass *klass)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS(klass);

  g_type_class_add_private(gobject_class, sizeof(CoilExpandablePrivate));

  gobject_class->set_property = coil_expandable_set_property;
  gobject_class->get_property = coil_expandable_get_property;
  gobject_class->finalize     = coil_expandable_finalize;

  /*
   * XXX: Override virtuals in sub-classes
   */

  klass->expand       = NULL;
  klass->equals       = NULL;
  klass->build_string = NULL;

  /*
   * Properties
   */

  g_object_class_install_property(gobject_class, PROP_CONTAINER,
      g_param_spec_object("container",
                          "The container of this struct.",
                          "set/get the container of this struct.",
                          COIL_TYPE_STRUCT,
                          G_PARAM_CONSTRUCT |
                          G_PARAM_READWRITE));

  g_object_class_install_property(gobject_class, PROP_EXPANDED,
      g_param_spec_boolean("expanded",
                           "Whether or not this object is marked as expanded.",
                           "get/set expanded",
                           FALSE,
                           G_PARAM_READWRITE));

  g_object_class_install_property(gobject_class, PROP_LOCATION,
      g_param_spec_pointer("location",
                         "Line, column, file of this instance.",
                         "get/set the location.",
                         G_PARAM_READWRITE));

  g_object_class_install_property(gobject_class, PROP_REAL_VALUE,
      g_param_spec_pointer("real_value",
                          "The result of expanding this object",
                          "get/set the expanded value",
                          G_PARAM_READWRITE));

}

static inline gboolean
_expandable_equals(const CoilExpandable  *x1,
                   const CoilExpandable  *x2,
                   GError               **error)
{
  CoilExpandableClass *klass;

  g_return_val_if_fail(COIL_IS_EXPANDABLE(x1), FALSE);
  g_return_val_if_fail(COIL_IS_EXPANDABLE(x2), FALSE);

  klass = COIL_EXPANDABLE_GET_CLASS(x1);

  if (klass->equals == NULL)
    g_error("Sub-class of CoilExpandable must "
            "define 'equals' class method.");

  return klass->equals(x1, x2, error);
}

COIL_API(gboolean)
coil_expandable_equals(gconstpointer  e1,
                       gconstpointer  e2,
                       GError       **error)
{
  const CoilExpandable *x1, *x2;

  g_return_val_if_fail(COIL_IS_EXPANDABLE(e1), FALSE);
  g_return_val_if_fail(COIL_IS_EXPANDABLE(e2), FALSE);

  x1 = COIL_EXPANDABLE(e1);
  x2 = COIL_EXPANDABLE(e2);

  return _expandable_equals(x1, x2, error);
}

COIL_API(gboolean)
coil_expandable_value_equals(const GValue  *v1,
                             const GValue  *v2,
                             GError       **error)
{
  const CoilExpandable *x1, *x2;

  g_return_val_if_fail(G_IS_VALUE(v1), FALSE);
  g_return_val_if_fail(G_IS_VALUE(v2), FALSE);

  if (!(G_VALUE_HOLDS(v1, COIL_TYPE_EXPANDABLE)
    && G_VALUE_HOLDS(v2, COIL_TYPE_EXPANDABLE)))
    return FALSE;

  x1 = COIL_EXPANDABLE(g_value_get_object(v1));
  x2 = COIL_EXPANDABLE(g_value_get_object(v2));

  return _expandable_equals(x1, x2, error);
}

COIL_API(inline gboolean)
coil_is_expanded(gconstpointer obj_ptr)
{
  const GObject *obj;

  g_return_val_if_fail(obj_ptr != NULL, FALSE);
  g_return_val_if_fail(G_IS_OBJECT(obj_ptr), FALSE);

  obj = G_OBJECT(obj_ptr);

  g_return_val_if_fail(COIL_IS_EXPANDABLE(obj), FALSE);

  return COIL_EXPANDABLE(obj)->priv->expanded;
}

COIL_API(inline gboolean)
coil_expand_value(GValue  *value,
                  GValue **real_value,
                  GError **error)
{
  return coil_expand_value_internal(value, real_value, NULL, error);
}

gboolean
coil_expand_value_internal(GValue      *value,
                           GValue     **real_value,
                           GHashTable  *visited,
                           GError     **error)
{
  CoilExpandable         *self;
  CoilExpandablePrivate  *priv;
  GError                 *internal_error = NULL;

  g_return_val_if_fail(G_IS_VALUE(value), FALSE);
  g_return_val_if_fail(G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE), FALSE);

  self = COIL_EXPANDABLE(g_value_get_object(value));
  priv = self->priv;

  if (!priv->expanded
    && !coil_expand(self, visited, &internal_error))
  {
    g_propagate_error(error, internal_error);
    return FALSE;
  }

  if (real_value != NULL)
    *real_value = (priv->real_value) ? priv->real_value : value;

  return TRUE;
}

COIL_API(gboolean)
coil_expand(gpointer     obj,
            GHashTable  *visited,
            GError     **error)
{
  CoilExpandable        *self;
  CoilExpandablePrivate *priv;
  CoilExpandableClass   *klass;
  GError                *internal_error = NULL;

  g_return_val_if_fail(COIL_IS_EXPANDABLE(obj), FALSE);

  self  = COIL_EXPANDABLE(obj);
  priv  = self->priv;
  klass = COIL_EXPANDABLE_GET_CLASS(self);

  if (G_UNLIKELY(klass->expand == NULL))
    g_error("Expandable class must define expand function.");

  if (priv->expanded)
    return TRUE;

  if (visited == NULL)
  {
    visited = g_hash_table_new_full(g_direct_hash, g_direct_equal,
                                    NULL, NULL);
  }
  else
    g_hash_table_ref(visited);

  if (g_hash_table_lookup_extended(visited, self,
                                  (gpointer *)NULL, (gpointer *)NULL))
  {
    coil_struct_set_error(error, self,
      "Cycle detected in value expansion.");

    goto fail;
  }

  g_hash_table_insert(visited, self, NULL);

  if (!klass->expand(self, visited, &internal_error))
  {
    g_propagate_error(error, internal_error);
    goto fail;
  }

  priv->expanded = TRUE;

  g_hash_table_unref(visited);
  return TRUE;

fail:
  g_hash_table_unref(visited);
  return FALSE;
}

