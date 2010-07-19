/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

G_DEFINE_TYPE(CoilLink, coil_link, COIL_TYPE_EXPANDABLE);

typedef enum
{
  PROP_0,
  PROP_PATH,
} CoilLinkProperties;

static GObject *
coil_link_constructor(GType                  gtype,
                      guint                  n_properties,
                      GObjectConstructParam *properties)
{
  GObject *object = G_OBJECT_CLASS(coil_link_parent_class)->constructor(
                              gtype, n_properties, properties);

  if (n_properties < 1)
    g_error("Link must be constructed with a path.");

  return object;
}


static void
coil_link_finalize(GObject *object)
{
  CoilLink *self = COIL_LINK(object);

  if (self->path)
    g_free(self->path);

  G_OBJECT_CLASS(coil_link_parent_class)->finalize(object);
}

static void
coil_link_set_property(GObject      *object,
                       guint         property_id,
                       const GValue *value,
                       GParamSpec   *pspec)
{
  CoilLink *self = COIL_LINK(object);

  switch (property_id)
  {
    case PROP_PATH:
      if (self->path)
        g_free(self->path);
      self->path = g_value_dup_string(value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
      break;
  }
}

static void
coil_link_get_property(GObject    *object,
                         guint       property_id,
                         GValue     *value,
                         GParamSpec *pspec)
{
  CoilLink *self = COIL_LINK(object);

  switch (property_id)
  {
    case PROP_PATH:
      g_value_set_string(value, self->path);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
      break;
  }
}

static void
coil_link_init(CoilLink *self)
{
  self->path = NULL;
}

static gboolean
_link_expand(CoilExpandable *super,
             GHashTable     *_visited,
             GError        **error)
{
  CoilLink *link;
  GValue   *value;
  GError   *internal_error = NULL;

  g_return_val_if_fail(super != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_LINK(super), FALSE);
  g_return_val_if_fail(super->container != NULL, FALSE);
  g_return_val_if_fail(_visited != NULL, FALSE);

  link = COIL_LINK(super);

  if (!COIL_PATH_IS_ABSOLUTE(link->path))
  {
    gchar resolved_path[COIL_PATH_BUFLEN];

    if (!coil_path_resolve(coil_struct_get_path(super->container),
            link->path, resolved_path, &internal_error))
      goto fail;

    value = coil_struct_get_path_value(super->container, resolved_path,
                                        FALSE, &internal_error);
  }
  else
  {
    value = coil_struct_get_path_value(super->container, link->path,
                                          FALSE, &internal_error);
  }

  if (G_UNLIKELY(internal_error))
    goto fail;

  g_assert(value != NULL);

  if (G_VALUE_HOLDS(value, COIL_TYPE_LINK)
    && !coil_expand_value_internal(value, &value,
                                  _visited, &internal_error))
    goto fail;

  g_assert_no_error(internal_error);

  g_object_set(G_OBJECT(super),
               "expanded", TRUE,
               "real_value", value,
               NULL);

  return TRUE;

fail:
  if (internal_error)
    g_propagate_error(error, internal_error);

  return FALSE;
}

COIL_API(gboolean)
coil_link_equals(gconstpointer e1,
                 gconstpointer e2,
                 GError        **error)
{
  const CoilLink       *l1, *l2;
  const CoilExpandable *x1, *x2;

  return TRUE;

  g_return_val_if_fail(COIL_IS_LINK(e1), FALSE);
  g_return_val_if_fail(COIL_IS_LINK(e2), FALSE);

  x1 = COIL_EXPANDABLE(e1);
  x2 = COIL_EXPANDABLE(e2);

  if (x1 == x2)
    return TRUE;

  // Check disjoint roots
  // XXX: this should probably cause an error
  //  or TODO: compare expanded (real) value.
  if (coil_struct_get_root(x1->container) !=
        coil_struct_get_root(x2->container))
    return FALSE;

  l1 = COIL_LINK(e1);
  l2 = COIL_LINK(e2);

  if (l1 == l2)
    return TRUE;

  gchar p1[COIL_PATH_BUFLEN];
  gchar p2[COIL_PATH_BUFLEN];

  if (!coil_path_resolve(coil_struct_get_path(x1->container),
                         l1->path, p1, error))
    return FALSE;

  if (!coil_path_resolve(coil_struct_get_path(x2->container),
                         l2->path, p2, error))
    return FALSE;

  return strcmp(p1, p2) == 0;
}

CoilLink *
coil_link_copy(const CoilLink *link)
{
  COIL_NOT_IMPLEMENTED(NULL);
}

static void
_link_build_string(CoilExpandable *expandable,
                   GString  *const buffer,
                   GError  **error /* ignored */)
{
  CoilLink *self;

  g_return_if_fail(expandable != NULL);
  g_return_if_fail(COIL_IS_LINK(expandable));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(error == NULL || *error == NULL); /* still wise */

  self = COIL_LINK(expandable);
  coil_link_build_string(self, buffer);
}

COIL_API(void)
coil_link_build_string(CoilLink *self,
                       GString  *const buffer)
{
  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_LINK(self));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(self->path != NULL);

  return g_string_append_printf(buffer, "=%s", self->path);
}

COIL_API(gchar *)
coil_link_to_string(const CoilLink *self)
{
  g_return_val_if_fail(self != NULL, NULL);
  g_return_val_if_fail(COIL_IS_LINK(self), NULL);
  g_return_val_if_fail(self->path != NULL, NULL);

  return g_strdup_printf("=%s", self->path);
}

static void
coil_link_class_init(CoilLinkClass *klass)
{
  GObjectClass        *gobject_class;
  CoilExpandableClass *expandable_class;

  gobject_class    = G_OBJECT_CLASS(klass);
  expandable_class = COIL_EXPANDABLE_CLASS(klass);

  gobject_class->constructor  = coil_link_constructor;
  gobject_class->set_property = coil_link_set_property;
  gobject_class->get_property = coil_link_get_property;
  gobject_class->finalize     = coil_link_finalize;

  expandable_class->expand       = _link_expand;
  expandable_class->equals       = coil_link_equals;
  expandable_class->build_string = _link_build_string;

  g_object_class_install_property(gobject_class, PROP_PATH,
      g_param_spec_string("path",
                          "The path the link points to.",
                          "set/get the path the link points to.",
                          NULL,
                          G_PARAM_READWRITE |
                          G_PARAM_CONSTRUCT));
}

