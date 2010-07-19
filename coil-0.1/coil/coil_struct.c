/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */

#include "coil.h"

G_DEFINE_TYPE(CoilStruct, coil_struct, COIL_TYPE_EXPANDABLE);

#define COIL_STRUCT_GET_PRIVATE(obj)  \
  (G_TYPE_INSTANCE_GET_PRIVATE ((obj), COIL_TYPE_STRUCT, CoilStructPrivate))

struct _CoilStructPrivate
{
  GHashTable    *key_table; // <gchar* -> GValue*>
  GHashTable    *path_table; // <gchar* -> GValue*>

  gchar         *name;
  gchar         *path;

  guint          size;
  guint          version;

  GList         *order;
  GList         *dependencies;
  GList         *expand_ptr;

  GStaticMutex  expand_lock;
};

typedef struct _StructItem
{
  gchar  *key;
  gchar  *path;
  GValue *value;
} StructItem;

typedef enum _StructItemType
{
  STRUCT_ITEM_KEY,
  STRUCT_ITEM_PATH,
  STRUCT_ITEM_VALUE,
} StructItemType;

/* CoilStruct Getter/Setter Properties */

typedef enum {
  PROP_0,
  /* */
  PROP_ALWAYS_EXPAND,
  PROP_DOC,
  PROP_NAME,
  PROP_PATH,
  PROP_IS_PROTOTYPE,
  PROP_REMEMBER_DEPS,
} CoilStructProperties;

enum
{
  CREATE,
  MODIFY,
  DESTROY,
  /* */
  LAST_SIGNAL
} CoilStructSignals;

/* Prototypes */

static gboolean
struct_delete_internal(CoilStruct   *self,
                       gchar        *key,
                       gchar        *path,
                       gboolean      skip_value_check,
                       gboolean      preserve_order,
                       StructItem   **preserved_item);

static void
struct_set_value_internal(CoilStruct *self,
                          gchar      *key,
                          gchar      *path,
                          GValue     *value,
                          gboolean    cast_prototype,
                          GError    **error);

static void
struct_rebuild_path_data(CoilStruct *self);

static void
struct_connect_expand_notify(CoilStruct *self,
                             CoilStruct *parent);

static guint struct_signals[LAST_SIGNAL] = { 0,};

#ifdef COIL_DEBUG

static void
debug_print_pair(const gchar *key,
                 const GValue *value)
{
  GValue cast_value = {0, };
  g_value_init(&cast_value, G_TYPE_STRING);
  g_value_transform(value, &cast_value);

  if (G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
    g_print("%s: {\n"
            "%s\n"
            "}\n", (gchar *)key,
            g_value_get_string(&cast_value));
  else
    g_print("%s: %s\n", (gchar *)key,
            g_value_get_string(&cast_value));

  g_value_unset(&cast_value);
}

/*
 * coil_struct_debug:
 *
 * Ouput debugging information for a CoilStruct.
 * Dumps the output of the key/path table and key/path list.
 *
 * @self: a CoilStruct
 */
COIL_API(void)
coil_struct_debug(CoilStruct *self)
{
  g_assert(COIL_IS_STRUCT(self));

  CoilStruct          *container;
  CoilStructPrivate   *priv;
  CoilExpandable      *super;
  GHashTableIter       it;
  gpointer             key, value;
  GList               *link;
  guint                n;

  priv      = self->priv;
  super     = COIL_EXPANDABLE(self);
  container = super->container;

  g_print("=============================================\n");
  g_print("Debugging Info for '%s'\n", priv->path);
  g_print("=============================================\n");

  g_print("\nName: %s\n"
            "Path: %s\n", priv->name, priv->path);

  if (container)
    g_print("Container: %s\n", container->priv->path);
  else
    g_print("No Container\n");

  CoilLocation *loc;

  g_object_get(G_OBJECT(self),
              "location", &loc,
              NULL);

  g_print("Location: " COIL_LOCATION_FORMAT "\n"
          "Size: %u\n",
          COIL_LOCATION_FORMAT_ARGS(*loc),
          priv->size);

  g_print("\nParents (@extends): \n");
  for (link = g_list_last(priv->dependencies), n = 1;
       link;
       link = g_list_previous(link))
  {
    if (G_VALUE_HOLDS(link->data, COIL_TYPE_LINK))
    {
      gchar *link_path = g_strdup_value_contents(link->data);
      g_print("    %u) %s", n++, link_path);
      g_free(link_path);
    }
  }

  g_print("\n\nIncludes: \n");

  g_print("\n\n-----------\n"
          "Path Table|"
          "\n-----------\n\n");

  if (g_hash_table_size(priv->path_table))
  {
    g_hash_table_iter_init(&it, priv->path_table);

    while (g_hash_table_iter_next(&it, &key, &value))
      debug_print_pair(key, value);
  }

  g_print("\n----------\n"
          "Key Table|\n"
          "----------\n\n");

  if (g_hash_table_size(priv->key_table))
  {
    g_hash_table_iter_init(&it, priv->key_table);

    while (g_hash_table_iter_next(&it, &key, &value))
      debug_print_pair(key, value);
  }

  g_print("\n----------\n"
          "Key Order|\n"
          "----------\n\n");
/*
  for (link = g_list_last(priv->key_order), n = 1;
       link;
       link = g_list_previous(link), n++)
    g_print("%u) %s\n", n, (gchar *)link->data);

  g_print("\n-----------\n"
          "Path Order|\n"
          "-----------\n\n");

  for (link = g_list_last(priv->path_order), n = 1;
       link;
       link = g_list_previous(link), n++)
    g_print("%u) %s\n", n, (gchar *)link->data);
*/

  /*
  g_print ("\n---------------\n"
           "Inherited Keys|\n"
           "---------------\n\n");

  GList *keys = coil_struct_get_inherited_keys(self);

  for (link = keys, n = 1;
       link;
       link = g_list_next(link), n++)
    g_print("%u) %s\n", n, (gchar *)link->data);
  g_list_free(keys);
  */

  g_print("\n###########################################\n");
}
#endif

static void
_struct_rebuild_path_data(CoilStruct *self)
{
  StructItem           *item;
  CoilStructPrivate    *const priv = self->priv;
  const GList          *order = priv->order;

  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));

  g_assert(order);

  do
  {
    gchar *new_path;

    item = (StructItem *)order->data;
    g_hash_table_remove(priv->path_table, item->path);

    new_path = coil_path_build(priv->path, item->key, NULL);
    g_hash_table_insert(priv->path_table, new_path, item->value);

    if (G_VALUE_HOLDS(item->value, COIL_TYPE_STRUCT))
    {
      CoilStruct *child = COIL_STRUCT(g_value_dup_object(item->value));

      if (child->priv->path)
        g_free(child->priv->path);

      child->priv->path = g_strdup(new_path);

      if (child->priv->size)
        _struct_rebuild_path_data(child);

      g_object_unref(child);
    }

    item->path = new_path;

  } while ((order = g_list_next(order)));
}

/*
 * struct_rebuild_path_data: Rebuilds internal data that depends on path
 *                          Call this after changing the contents of path.
 *
 * @self: A CoilStruct instance.
 */
static void
struct_rebuild_path_data(CoilStruct *self)
{
  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));

  CoilStructPrivate *priv = self->priv;

  if (!priv->size)
    return;

  StructItem *first_item = (StructItem *)priv->order->data;

  if (coil_path_has_container(first_item->key, priv->path))
    return;

  _struct_rebuild_path_data(self);
}

/*
 * coil_struct_constructor: CoilStruct constructor
 */
static GObject *
coil_struct_constructor (GType                  gtype,
                         guint                  n_properties,
                         GObjectConstructParam *properties)
{
  GObject *object = G_OBJECT_CLASS(coil_struct_parent_class)->constructor(
                              gtype, n_properties, properties);

  CoilStruct        *self, *container;
  CoilStructPrivate *priv;
  CoilExpandable    *super;

  self      = COIL_STRUCT(object);
  priv      = self->priv;
  super     = COIL_EXPANDABLE(object);
  container = super->container;

  if (priv->path && !priv->name)
  {
    priv->name = coil_path_get_key(priv->path);
  }

  /* struct is a child of another struct */
  if (priv->name && container)
  {
    if (!priv->path)
      priv->path = coil_path_build(container->priv->path,
                                   priv->name,
                                   NULL);

    priv->path_table = g_hash_table_ref(container->priv->path_table);
  }
  else if (!container) /* struct is @root */
  {
    if (!priv->path)
      priv->path = g_strndup(COIL_ROOT_PATH, COIL_ROOT_PATH_LEN);

    priv->path_table = g_hash_table_new_full(coil_str_hash, g_str_equal,
                                             g_free, NULL);
  }
  else
    g_error("A name must be specified with a container.");

  g_object_set(G_OBJECT(self),
               "expanded", TRUE,
               NULL);

  g_signal_emit(self,
                struct_signals[CREATE],
                coil_struct_is_prototype(self) ?
                    g_quark_from_static_string("prototype") : 0);

  return object;
}

/*
 * coil_struct_clear: Clear all keys and values in CoilStruct
 *
 * @self: A CoilStruct instance.
 */
COIL_API(void)
coil_struct_clear(CoilStruct *self)
{
  CoilStructPrivate *priv;
  register GList    *order;

  g_return_if_fail(COIL_IS_STRUCT(self));

  priv = self->priv;

  //g_signal_emit(self, struct_signals[MODIFY], 0);

  if (priv->dependencies)
  {
    free_value_list(priv->dependencies);
    priv->dependencies = NULL;
  }

  for (order = priv->order;
       order != NULL;
       order = g_list_delete_link(order, order))
  {
    g_hash_table_remove(priv->path_table, (gchar *)((StructItem *)order->data)->path);
    g_free(order->data);
  }

  g_hash_table_remove_all(priv->key_table);

  priv->order      = NULL;
  priv->expand_ptr = NULL;

  priv->size       = 0;
  priv->version    = 0;
}

/*
 * coil_struct_finalize: Finalize function for CoilStruct
 */
static void
coil_struct_finalize(GObject *gobject)
{
  CoilStruct        *self;
  CoilStructPrivate *priv;

  self = COIL_STRUCT(gobject);
  priv = self->priv;

  //g_signal_emit(self, struct_signals[DESTROY], 0);

  //g_signal_handlers_block_by_func(self,
  coil_struct_clear(self);

  if (priv->key_table)
  {
    g_hash_table_unref(priv->key_table);
    priv->key_table = NULL;
  }

  if (priv->path_table)
  {
    g_hash_table_unref(priv->path_table);
    priv->path_table = NULL;
  }

  if (priv->order)
  {
    register GList *op = priv->order;
    do
    {
      g_free(op->data);
      op = g_list_delete_link(op, op);
    } while (op != NULL);
    priv->order = NULL;
  }

  if (self->doc)
    g_free(self->doc);

  if (priv->name)
    g_free(priv->name);

  if (priv->path)
    g_free(priv->path);

  g_static_mutex_free(&priv->expand_lock);

  // g_signal_handlers_unblock_by_func

  G_OBJECT_CLASS(coil_struct_parent_class)->finalize(gobject);
}

/*
 * coil_struct_set_property: Setter for CoilStruct properties
 */
static void
coil_struct_set_property(GObject      *object,
                         guint         property_id,
                         const GValue *value,
                         GParamSpec   *pspec)
{
  CoilStruct        *self;
  CoilStructPrivate *priv;

  self = COIL_STRUCT(object);
  priv = self->priv;

  switch (property_id)
  {
    case PROP_ALWAYS_EXPAND:
      self->always_expand = g_value_get_boolean(value);
      break;

    case PROP_DOC:
      if (self->doc)
        g_free(self->doc);
      self->doc = g_value_dup_string(value);
      break;

    case PROP_NAME:
      if (priv->name)
        g_free(priv->name);
      priv->name = g_value_dup_string(value);
      break;

    case PROP_PATH:
      if (priv->path)
        g_free(priv->path);
      priv->path = g_value_dup_string(value);
      break;

    case PROP_IS_PROTOTYPE:
      self->is_prototype = g_value_get_boolean(value);
      //g_object_notify(G_OBJECT(self), "is-prototype");
      break;

    case PROP_REMEMBER_DEPS:
      self->remember_deps = g_value_get_boolean(value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
      break;
  }
}

/*
 * coil_struct_get_property: Getter for CoilStruct properties.
 */
static void
coil_struct_get_property(GObject      *object,
                         guint         property_id,
                         GValue       *value,
                         GParamSpec   *pspec)
{
  CoilStruct        *self;
  CoilStructPrivate *priv;

  self = COIL_STRUCT(object);
  priv = self->priv;

  switch (property_id)
  {
      case PROP_ALWAYS_EXPAND:
        g_value_set_boolean(value, self->always_expand);
        break;

      case PROP_DOC:
        g_value_set_string(value, self->doc);
        break;

      case PROP_NAME:
        g_value_set_string(value, priv->name);
        break;

      case PROP_PATH:
        g_value_set_string(value, priv->path);
        break;

      case PROP_IS_PROTOTYPE:
        g_value_set_boolean(value, self->is_prototype);
        break;

      case PROP_REMEMBER_DEPS:
        g_value_set_boolean(value, self->remember_deps);
        break;

      default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
        break;
  }
}

/*
 * coil_struct_init: CoilStruct init function.
 */
static void
coil_struct_init (CoilStruct *self)
{
  CoilStructPrivate *priv;

  self->priv = COIL_STRUCT_GET_PRIVATE(self);
  priv = self->priv;

  /* default everything */

  self->always_expand = FALSE;
  self->doc           = NULL;
  self->remember_deps = FALSE;
  self->is_prototype  = FALSE;
  priv->version       = 0;
  priv->size          = 0;
  priv->expand_ptr    = NULL;
  priv->dependencies  = NULL;
  priv->order         = NULL;
  priv->name          = NULL;
  priv->path          = NULL;
  priv->path_table    = NULL;
  priv->key_table     = g_hash_table_new_full(coil_str_hash,
                                              g_str_equal,
                                              g_free,
                                              free_value);

  g_static_mutex_init(&priv->expand_lock);
}

/* coil_struct_is_root:
 *
 * @self: an instance of a coil struct object
 *
 * Return Value: TRUE if the object is a root node.
 */

COIL_API(gboolean)
coil_struct_is_root(const CoilStruct *self)
{
  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  return COIL_EXPANDABLE(self)->container == NULL;
}

COIL_API(gboolean)
coil_struct_is_prototype(const CoilStruct *self)
{
  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  return self->is_prototype;
}

COIL_API(gboolean)
coil_struct_is_empty(const CoilStruct *self)
{
  CoilStructPrivate *priv;

  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  priv = self->priv;

  return !(priv->size || priv->dependencies);
}

COIL_API(gboolean)
coil_struct_is_ancestor(const CoilStruct *parent,
                        const CoilStruct *child)
{
  const CoilStruct *container;

  g_return_val_if_fail(COIL_IS_STRUCT(parent), FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(child), FALSE);

  container = child;
  while ((container = COIL_EXPANDABLE(container)->container))
  {
    if (container == parent)
      return TRUE;
  }

  return FALSE;
}

COIL_API(gboolean)
coil_struct_is_descendent(const CoilStruct *child,
                          const CoilStruct *parent)
{
  g_return_val_if_fail(COIL_IS_STRUCT(child), FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(parent), FALSE);

  return coil_struct_is_ancestor(parent, child);
}

/* coil_struct_get_root:
 *
 * @self: an instance of a coil struct object
 *
 * Return Value: the root struct of the first argument, or the first
 *               argument if it is the root.
 */
COIL_API(CoilStruct *)
coil_struct_get_root(const CoilStruct *self)
{
  const CoilStruct *root, *container;

  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);

  root = (CoilStruct *)self;
  while ((container = COIL_EXPANDABLE(root)->container))
    root = container;

  return (CoilStruct *)root;
}

COIL_API(gboolean)
coil_struct_has_same_root(const CoilStruct *a,
                          const CoilStruct *b)
{
  g_return_val_if_fail(a != NULL, FALSE);
  g_return_val_if_fail(b != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(a), FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(b), FALSE);

  if (a == b)
    return TRUE;

  return coil_struct_get_root(a) == coil_struct_get_root(b);
}

COIL_API(const gchar *)
coil_struct_get_path(const CoilStruct *self)
{
  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);

  return (const gchar *)self->priv->path;
}

void
coil_struct_foreach_container(CoilStruct     *self,
                              CoilStructFunc  func,
                              gpointer        user_data)
{
  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(func != NULL);

  CoilStruct *container = self;
  gboolean    keep_going;

  do
  {
    keep_going = (*func) (container, user_data);
    container = COIL_EXPANDABLE(container)->container;
  } while (keep_going && container);

}

static gboolean
_cast_prototype_to_real(CoilStruct *self, gpointer user_data)
{
  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  if (coil_struct_is_prototype(self))
  {
    g_object_set(self,
                 "is-prototype", FALSE,
                 NULL);

    return TRUE;
  }

  return FALSE;
}

static CoilStruct *
create_containers(CoilStruct  *self,
                  const gchar *container_path,
                  gboolean     is_prototype,
                  GError     **error)
{
  CoilStructPrivate *const priv = self->priv;
  CoilStruct        *container, *next_container;
  CoilExpandable    *super;
  GValue            *value;
  register gchar    *key;
  gchar              path[COIL_PATH_BUFLEN];
  guint              missing, len;

  g_return_val_if_fail(self != NULL, NULL);
  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);
  g_return_val_if_fail(container_path != NULL, NULL);

  if (COIL_PATH_IS_ROOT(container_path))
    return coil_struct_get_root(self);

  super = COIL_EXPANDABLE(self);
  len = strlen(container_path);

  g_assert(len < COIL_PATH_BUFLEN);

  memcpy(path, container_path, len);
  key = path + len;
  *key = '\0';

  /* find the first container that does exists
   * and count the missing keys
   */
  for (missing = 0;
      key >= path &&
       len > COIL_ROOT_PATH_LEN;
       missing++)
  {
    if ((value = g_hash_table_lookup(priv->path_table, path)))
    {
      if (!G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
      {
        g_set_error(error,
                    COIL_ERROR,
                    COIL_ERROR_PATH,
                    "Attempting to create children in non-struct object %s.",
                    container_path);

        return NULL;
      }

      container = COIL_STRUCT(g_value_get_object(value));

      if (!is_prototype &&
          coil_struct_is_prototype(container))
      {
        coil_struct_foreach_container(container, _cast_prototype_to_real, NULL);
      }

      /* value exists */
      break;
    }

    /* value does not exist */
    /* pop off a key for the next container */
    do
    {
      len--;
    } while (*--key != COIL_PATH_DELIM);

    *key = '\0';
  } // .. for

  //g_debug("num_missing = %d", missing);

  if (G_UNLIKELY(len == COIL_ROOT_PATH_LEN))
    container = coil_struct_get_root(self);
  else
    container = COIL_STRUCT(g_value_get_object(value));

  /* add a container for each missing key */
  while (missing--)
  {
    *key++ = COIL_PATH_DELIM;
    const guint klen = strlen(key);

    next_container = coil_struct_new("container", container,
                                     "name", key,
                                     "path", path,
                                     "is-prototype", is_prototype,
                                     "location", &super->location);

    new_value(value, COIL_TYPE_STRUCT,
              take_object, next_container);

    struct_set_value_internal(container,
                              g_strndup(key, klen),
                              g_strdup(path),
                              value,
                              FALSE,
                              NULL);

    container = next_container;
    key += klen;
  }

  return container;
}

static void
struct_set_value_internal(CoilStruct *self,
                          gchar      *key,
                          gchar      *path,
                          GValue     *value,
                          gboolean    cast_prototype,
                          GError    **error)
{
  CoilStructPrivate *priv;
  GValue            *old_value;
  GError            *internal_error = NULL;

  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(G_IS_VALUE(value));
  g_return_if_fail(key != NULL);
  g_return_if_fail(path != NULL);
  g_return_if_fail(error == NULL || *error == NULL);

  priv = self->priv;

  /* Notify dependents that we're changing */
  g_signal_emit(self, struct_signals[MODIFY],
                0, (gpointer *)&internal_error);

  if (G_UNLIKELY(internal_error))
  {
    g_propagate_error(error, internal_error);
    return;
  }

  old_value = g_hash_table_lookup(priv->path_table, path);

  /* check if a value already exists for path */
  if (!old_value)
  {
    /* value does NOT exist for key/path already */
    StructItem *item = g_new(StructItem, 1);
    item->key = key;
    item->path = path;
    item->value = value;
    priv->order = g_list_prepend(priv->order, item);
  }
  else
  {
    if (G_VALUE_HOLDS(old_value, COIL_TYPE_STRUCT))
    {
      /* Check if we're overwriting a prototype
       * we merge the keys we're constructing with and destroy
       * the surrogate struct.
       */
      CoilStruct *const node = COIL_STRUCT(g_value_get_object(old_value));
      if (node
          && coil_struct_is_prototype(node)
          && G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
      {
        CoilStruct *const src = COIL_STRUCT(g_value_get_object(value));

        coil_struct_merge(src, node, TRUE, &internal_error);

        if (G_UNLIKELY(internal_error))
        {
          g_propagate_error(error, internal_error);
          return;
        }

        g_free(key);
        g_free(path);
        free_value(value);

        g_object_set(G_OBJECT(node),
                     "is-prototype", FALSE,
                     NULL);

        return;
      }
    }

    /* value exists, delete but preserve key order */
    StructItem *preserved_item = NULL;
    if (struct_delete_internal(self, key, path,
                               TRUE, TRUE, &preserved_item)
      && preserved_item != NULL)
      preserved_item->value = value;
    else
      g_assert_not_reached();
  }

  /* if value is struct,
   * the path will be different so we need up update that and
   * also update children */
  if (G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
  {
    CoilStruct     *node;
    CoilExpandable *super;

    node  = COIL_STRUCT(g_value_get_object(value));
    super = COIL_EXPANDABLE(node);

    if (!coil_struct_is_descendent(node, self))
    {
      g_hash_table_unref(node->priv->path_table);
      node->priv->path_table = g_hash_table_ref(priv->path_table);
    }

    g_object_set(G_OBJECT(node),
                 "container", self,
                 "name", key,
                 "path", path,
                 NULL);

    struct_rebuild_path_data(node);
  }
  else if (G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE))
  {
    CoilExpandable *object = COIL_EXPANDABLE(g_value_get_object(value));
    if (object->container != self)
    {
      g_object_set(G_OBJECT(object),
                  "container", self,
                  NULL);
    }
  }

  g_hash_table_insert(priv->path_table, path, value);
  g_hash_table_insert(priv->key_table, key, value);

  priv->version++;
  priv->size++;

  if (cast_prototype && coil_struct_is_prototype(self))
    coil_struct_foreach_container(self, _cast_prototype_to_real, NULL);
}


/*
 * coil_struct_set_path_value:
 *
 * @self: a coil struct instance
 * @path: the path to set
 * @value: the GValue to set
 * @error: a GError object or %NULL
 *
 * Description: Set a path to a value in a struct. This is most likely
 *    what you should be calling from a binding.
 *
 */
COIL_API(void)
coil_struct_set_path_value(CoilStruct *self,
                           gchar      *_path,
                           GValue     *value,
                           GError    **error)
{
  g_assert(self != NULL);
  g_assert(COIL_IS_STRUCT(self));

  g_return_if_fail(_path != NULL);

  CoilStructPrivate *const priv = self->priv;
  CoilStruct        *container;
  GError            *internal_error = NULL;
  gchar              container_path[COIL_PATH_BUFLEN];
  gchar              key[COIL_PATH_BUFLEN];
  gchar              path[COIL_PATH_BUFLEN];

  coil_path_resolve_full(priv->path, _path,
                         path, container_path, key,
                         &internal_error);

  if (G_UNLIKELY(internal_error))
  {
    g_propagate_error(error, internal_error);
    return;
  }

  if ((container = create_containers(self, container_path, FALSE, error)))
  {
    struct_set_value_internal(container,
                              g_strdup(key),
                              g_strdup(path),
                              value,
                              TRUE,
                              error);

  }
}

/*
 * coil_struct_set_key_value:
 *
 * @self: a coil struct instance
 * @key: the key to set
 * @value: the GValue to set
 * @error: A GError object or %NULL
 *
 */
COIL_API(void)
coil_struct_set_key_value(CoilStruct    *self,
                          gchar         *key,
                          GValue        *value,
                          GError       **error)
{
  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));

  g_return_if_fail(key != NULL);

  CoilStructPrivate *const priv = self->priv;

  struct_set_value_internal(self,
                            key,
                            coil_path_build(priv->path, key, NULL),
                            value,
                            TRUE,
                            error);
}

/*
 * struct_delete_internal:
 *
 * @self: The CoilStruct container for key/path
 * @key: the key to delete
 * @path: the path to delete, corresponds to struct + key
 * @error: a GError pointer or %NULL
 *
 * Description: this function is called when both key and path have been
 *              obtained for a given deletion.
 *
 */
static gboolean
struct_delete_internal(CoilStruct   *self,
                       gchar        *key,
                       gchar        *path,
                       gboolean      skip_value_check,
                       gboolean      preserve_order,
                       StructItem **preserved_item)
{
  CoilStructPrivate *priv;
  GValue            *value = NULL;
  register GList    *order;
  gboolean           found;

  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(!self->is_prototype, FALSE);

  g_return_val_if_fail(key != NULL, FALSE);
  g_return_val_if_fail(path != NULL, FALSE);

  priv = self->priv;

  //g_signal_emit(self, struct_signals[MODIFY], 0);

  if (!skip_value_check)
  {
    found = g_hash_table_lookup_extended(priv->key_table, key,
                                         (gpointer *)NULL, (gpointer *)&value);

    if (!(priv->size && found && value != NULL))
    {
      if (!(found || coil_struct_is_root(self)))
      {
        /* XXX: Safe to ignore error below:
         *  - Self is not root,
         *  - Not deleting first-order key
         *  - Not marking duplicate delete
         */
        coil_struct_mark_key_deleted(self, g_strdup(key), NULL);
      }

      return FALSE;
    }

    g_assert(found == TRUE);
  }

  if (coil_struct_is_empty(self))
    return FALSE;

  found = FALSE;
  order = priv->order;

  g_assert(order);

  /* remove the key/path from order list */
  do
  {
    StructItem *item = (StructItem *)order->data;
    if (strcmp(item->key, key) == 0)
    {
      if (preserve_order)
      {
        item->key = key;
        item->path = path;
        item->value = NULL;

        if (preserved_item)
          *preserved_item = item;
      }
      else
      {
        g_free(item);
        priv->order = g_list_delete_link(priv->order, order);
      }

      g_hash_table_remove(priv->path_table, path);
      g_hash_table_remove(priv->key_table, key);

      priv->size--;
      priv->version++;
      found = TRUE;

      break;
    }
  } while ((order = g_list_next(order)));

  g_assert(found == TRUE);

  return TRUE;
}

/*
 * coil_struct_delete_path:
 *
 * @self: a CoilStruct instance
 * @path: the path to delete, probably a good idea to exist in 'self'
 * @error: a GError object or %NULL
 *
 * Description: Deletes a path from struct. Frees all memory associated with
 *            the insertion of that path/key.
 *
 */
COIL_API(gboolean)
coil_struct_delete_path(CoilStruct   *self,
                        const gchar  *_path,
                        GError      **error)
{
  gchar              key[COIL_PATH_BUFLEN];
  gchar              path[COIL_PATH_BUFLEN];
  gchar              container_path[COIL_PATH_BUFLEN];
  CoilStruct        *container;
  CoilStructPrivate *priv;
  GValue            *container_value;
  GError            *internal_error;

  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(_path != NULL, FALSE);

  priv           = self->priv;
  internal_error = NULL;

  if (!coil_path_resolve_full(priv->path, _path,
                              path, container_path, key,
                              &internal_error))
  {
    g_propagate_error(error, internal_error);
    return FALSE;
  }

  if (COIL_PATH_IS_ROOT(container_path))
    container = coil_struct_get_root(self);
  else
  {
    container_value = g_hash_table_lookup(priv->path_table, container_path);

    if (G_UNLIKELY(!container_value))
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_PATH,
                  "Container path '%s' not found in '%s'.",
                  container_path, priv->path);

      return FALSE;
    }

    if (G_UNLIKELY(!G_IS_VALUE(container_value))
      || G_UNLIKELY(!G_VALUE_HOLDS(container_value, COIL_TYPE_STRUCT)))
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_PATH,
                  "Container path '%s' of '%s' is not a container.",
                  container_path, path);

      return FALSE;
    }

    container = COIL_STRUCT(g_value_get_object(container_value));
  }

  return struct_delete_internal(container, key, path,
                                FALSE, FALSE, NULL);
}

/*
 * coil_struct_delete_key:
 *
 * @self: a CoilStruct instance
 * @key: the key to delete, must exist inside self
 * @error: a GError pointer or %NULL.
 *
 * Description: Deletes a known key from a struct. Frees all memory associated
 *            with the insertion of that key.
 *
 */
COIL_API(gboolean)
coil_struct_delete_key(CoilStruct  *self,
                       const gchar *key)
{
  gchar path[COIL_PATH_BUFLEN];

  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(key != NULL, FALSE);

  coil_path_build_buffer(path, self->priv->path, key, NULL);
  return struct_delete_internal(self, (gchar *)key, path,
                                FALSE, FALSE, NULL);
}

COIL_API(void)
coil_struct_mark_path_deleted(CoilStruct  *self,
                              const gchar *_path,
                              CoilStruct **_container,
                              GError     **error)
{
  CoilStruct        *container;
  CoilStructPrivate *priv = self->priv;
  GValue            *value;
  gchar              container_path[COIL_PATH_BUFLEN];
  gchar              path[COIL_PATH_BUFLEN];
  gchar              key[COIL_PATH_BUFLEN];

  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(_path != NULL);
  g_return_if_fail(_container == NULL || *_container == NULL);

  if (!coil_path_resolve_full(priv->path, _path,
                        path, container_path, key, error))
    return;

  if (COIL_PATH_IS_ROOT(container_path))
  {
     coil_struct_set_error(error, self,
          "Keys in root cannot be marked as deleted."
          "ALL keys in root are first-order.");

    return;
  }

  if (!coil_path_is_descendent(path, priv->path))
  {
    coil_struct_set_error(error, self,
      "deleted keys must be properties (or descendents) of struct.");

    return;
  }

  if ((value = g_hash_table_lookup(priv->path_table, container_path)) != NULL)
  {
    container = COIL_STRUCT(g_value_get_object(value));

    if (coil_struct_is_deleted_key(container, key))
    {
      coil_struct_set_error(error, self,
        "Attempting to delete '%s' (%s) twice.", key, path);

      return;
    }
    else if (coil_struct_contains_key(container, key, FALSE))
    {
      coil_struct_set_error(error, self,
        "Attempting to delete first-order key '%s' (%s).", key, path);

      return;
    }
  }
  else if (!(container = create_containers(self, container_path, FALSE, error)))
    return;

  //g_signal_emit(self, struct_signals[MODIFY], 0);

  priv = container->priv;
  g_hash_table_insert(priv->key_table, g_strdup(key), NULL);
  priv->version++;

  if (_container != NULL)
    *_container = container;
}

COIL_API(void)
coil_struct_mark_key_deleted(CoilStruct  *self,
                             gchar       *key,
                             GError     **error)
{
  CoilStructPrivate *priv;

  g_return_if_fail(self != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(key != NULL);

  priv = self->priv;

  if (coil_struct_is_root(self))
  {
    coil_struct_set_error(error, self,
        "Keys in root cannot be marked as deleted."
        "ALL keys in root are first-order.");

    return;
  }

  if (coil_struct_is_deleted_key(self, key))
  {
    coil_struct_set_error(error, self,
      "Attempting to delete key '%s' twice.", key);

    return;
  }

  if (coil_struct_contains_key(self, key, FALSE))
  {
    coil_struct_set_error(error, self,
      "Attempting to delete first-order key '%s'.", key);

    return;
  }

  //g_signal_emit(self, struct_signals[MODIFY], 0);
  g_hash_table_insert(priv->key_table, key, NULL);
  priv->version++;
}

COIL_API(gboolean)
coil_struct_is_deleted_key(const CoilStruct  *self,
                           const gchar *key)
{
  GValue            *value;
  gboolean           key_exists;
  CoilStructPrivate *priv;

  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(key != NULL, FALSE);

  if (/*coil_struct_is_root(self)
    || */coil_struct_is_empty(self))
    return FALSE;

  priv = self->priv;
  key_exists = g_hash_table_lookup_extended(priv->key_table, key,
                                            (gpointer *)NULL, (gpointer *)&value);

  return (key_exists && value == NULL);
}

COIL_API(gboolean)
coil_struct_is_deleted_path(const CoilStruct *self,
                            const gchar *path)
{
  CoilStruct        *container;
  CoilStructPrivate *priv;

  gchar container_path[COIL_PATH_BUFLEN];
  gchar key[COIL_PATH_BUFLEN];

  g_return_val_if_fail(self != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(path != NULL, FALSE);

  if (coil_struct_is_empty(self))
    return FALSE;

  priv = self->priv;

  if (!coil_path_resolve_full(priv->path, path, NULL,
                              container_path, key, NULL)
    || !(container = g_hash_table_lookup(priv->path_table, container_path)))
    return FALSE;

  return coil_struct_is_deleted_key(container, key);
}


COIL_API(gboolean)
coil_struct_has_dependency(CoilStruct *self,
                      GType       type,
                      gpointer    object)
{

  GList             *dep;
  GObject           *o1, *o2;
  CoilStructPrivate *priv;

  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  priv = self->priv;

  if (priv->dependencies == NULL)
    return FALSE;

  o1 = G_OBJECT(object);

  for (dep = priv->dependencies;
       dep != NULL;
       dep = g_list_next(dep))
  {
    if (G_VALUE_HOLDS((GValue *)dep->data, type))
    {
      o2 = G_OBJECT(g_value_get_object(dep->data));
      if (o1 == o2)
        return TRUE;
    }
  }

  return FALSE;
}

COIL_API(void)
coil_struct_add_dependency(CoilStruct *self,
                           GType       type,
                           gpointer    object)
{
  CoilStructPrivate *priv;
  GValue            *dependency;

  g_return_if_fail(COIL_IS_STRUCT(self));

  priv = self->priv;

  new_value(dependency, type, set_object, object);
  priv->dependencies = g_list_prepend(priv->dependencies, dependency);
  priv->version++;

  g_object_set(G_OBJECT(self),
               "expanded", FALSE,
               NULL);
}

static GError *
_struct_expand_notify_cb(GObject *instance,
                         gpointer data)
{
  g_return_val_if_fail(instance != NULL, NULL);
  g_return_val_if_fail(data != NULL, NULL);
  g_return_val_if_fail(COIL_IS_STRUCT(instance), NULL);
  g_return_val_if_fail(COIL_IS_STRUCT(data), NULL);

  CoilStruct *parent = COIL_STRUCT(instance);
  GError     *internal_error = NULL;

//  g_debug("expand notify for %s", coil_struct_get_path(data));
  g_assert(1 == g_signal_handlers_disconnect_matched(instance,
                                                     G_SIGNAL_MATCH_FUNC |
                                                     G_SIGNAL_MATCH_DATA,
                                                     0, 0, NULL,
                                                     G_CALLBACK(_struct_expand_notify_cb),
                                                     data));

  coil_expand(data, NULL, &internal_error);

  return internal_error;
}

static void
_prototype_expand_notify_cb(GObject *instance,
                            GParamSpec *arg1,
                            gpointer data)
{
  g_return_if_fail(instance != NULL);
  g_return_if_fail(data != NULL);
  g_return_if_fail(COIL_IS_STRUCT(instance));
  g_return_if_fail(COIL_IS_STRUCT(data));

  CoilStruct *self, *parent;

  self   = COIL_STRUCT(data);
  parent = COIL_STRUCT(instance);

  if (!coil_struct_is_prototype(parent))
  {
//    g_debug("prototype notify for %s", coil_struct_get_path(parent));
    g_assert(1 == g_signal_handlers_disconnect_matched(instance,
                                                       G_SIGNAL_MATCH_FUNC |
                                                       G_SIGNAL_MATCH_DATA,
                                                       0, 0, NULL,
                                                       G_CALLBACK(_prototype_expand_notify_cb),
                                                       data));
    g_signal_connect(instance, "modify",
                     G_CALLBACK(_struct_expand_notify_cb), self);
  }
}

static void
struct_connect_expand_notify(CoilStruct *const self,
                             CoilStruct *const parent)
{
  g_return_if_fail(self != NULL);
  g_return_if_fail(parent != NULL);
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(COIL_IS_STRUCT(parent));

  if (coil_struct_is_prototype(parent))
  {
    g_signal_connect(G_OBJECT(parent), "notify::is-prototype",
                     G_CALLBACK(_prototype_expand_notify_cb), self);
  }
  else
  {
    g_signal_connect(G_OBJECT(parent), "modify",
                     G_CALLBACK(_struct_expand_notify_cb), self);
  }
}

COIL_API(void)
coil_struct_extend_path(CoilStruct  *self,
                        const gchar *_path,
                        GError      **error)
{
  CoilStruct        *parent;
  CoilStructPrivate *const priv = self->priv;
  gchar              parent_path[COIL_PATH_BUFLEN];
  GValue            *value;
  GError            *resolve_error = NULL;

  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(_path != NULL);

  if(COIL_PATH_IS_ROOT(_path))
  {
    coil_struct_set_error(error, self,
      "@extends target cannot be @root.");

    return;
  }

  coil_path_resolve(priv->path, _path,
                    parent_path, &resolve_error);

  if (G_UNLIKELY(resolve_error))
  {
    g_propagate_error(error, resolve_error);
    return;
  }

  if (COIL_PATH_IS_ROOT(parent_path))
  {
    coil_struct_set_error(error, self,
        "@root cannot extend.");

    return;
  }

  if (coil_path_is_descendent(parent_path, priv->path))
  {
    coil_struct_set_error(error, self,
        "@extends target '%s' cannot be children of container.", _path);

    return;
  }

  if (coil_path_is_descendent(priv->path, parent_path))
  {
    coil_struct_set_error(error, self,
        "@extend target '%s' cannot be ancestor of struct.", _path);

    return;
  }

  if (strcmp(priv->path, parent_path) == 0)
  {
    coil_struct_set_error(error, self,
      "@extends target '%s' cannot be struct itself.", _path);

    return;
  }

  value = g_hash_table_lookup(priv->path_table, parent_path);

  if (value != NULL)
  {
    if (!G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
    {
      coil_struct_set_error(error, self,
        "@extends target '%s' must be a struct.", _path);

      return;
    }

    parent = COIL_STRUCT(g_value_get_object(value));

    if (!coil_struct_is_prototype(parent)
      && coil_struct_is_empty(parent))
      return;

  }
  else if (!(parent = create_containers(self, parent_path, TRUE, error)))
    return;

  if (coil_struct_has_dependency(self, COIL_TYPE_STRUCT, parent))
  {
    coil_struct_set_error(error, self,
      "double @extends for target '%s'.", _path);

    return;
  }

  coil_struct_add_dependency(self, COIL_TYPE_STRUCT, parent);

  if (self->always_expand)
    coil_struct_expand(self, error);
  else
    struct_connect_expand_notify(self, parent);
}

COIL_API(void)
coil_struct_extend(CoilStruct *self,
                   CoilStruct *parent,
                   GError     **error)
{
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(!self->is_prototype);
  g_return_if_fail(COIL_IS_STRUCT(parent));

  if (!coil_struct_is_prototype(parent)
      && coil_struct_is_empty(parent))
    return;

  if (self == parent)
  {
    coil_struct_set_error(error, self,
      "cannot extend self.");

    return;
  }

  if (coil_struct_is_root(self))
  {
    coil_struct_set_error(error, self,
        "@root cannot extend");

    return;
  }

  if (coil_struct_is_root(parent))
  {
    coil_struct_set_error(error, self,
      "@extends target cannot be @root.");

    return;
  }

  if (coil_struct_is_ancestor(parent, self))
  {
    coil_struct_set_error(error, self,
      "cannot extend parent containers.");

    return;
  }

  if (coil_struct_is_descendent(parent, self))
  {
    coil_struct_set_error(error, self,
      "cannot extend children.");

    return;
  }

  if (coil_struct_get_root(self) != coil_struct_get_root(parent))
  {
    coil_struct_set_error(error, self,
      "cannot extend structs in disjoint roots.");

    return;
  }

  if (coil_struct_has_dependency(self, COIL_TYPE_STRUCT, parent))
  {
    coil_struct_set_error(error, self,
      "double @extends for path %s", parent->priv->path);

    return;
  }

  if (coil_struct_is_empty(parent))
    return;

  coil_struct_add_dependency(self, COIL_TYPE_STRUCT, parent);

  if (self->always_expand)
    coil_struct_expand(self, error);
  else
    struct_connect_expand_notify(self, parent);
}

COIL_API(void)
coil_struct_iter_init(CoilStructIter *iter,
                      const CoilStruct *node)
{
  CoilStructPrivate *priv;

  g_return_if_fail(COIL_IS_STRUCT(node));
  g_return_if_fail(!node->is_prototype);
  g_return_if_fail(iter != NULL);
  g_return_if_fail(node != NULL);

  priv = node->priv;

  iter->node = node;
  iter->version = priv->version;
  iter->position = g_list_last(priv->order);
}

COIL_API(gboolean)
coil_struct_iter_next(CoilStructIter *iter,
                      gchar          **key,
                      gchar          **path,
                      GValue         **value)
{
  const CoilStruct *node;
  const StructItem  *item;

  g_return_val_if_fail(iter != NULL, FALSE);

  if (!iter->position)
    return FALSE;

  node = iter->node;
  item = (StructItem *)iter->position->data;

  g_return_val_if_fail(iter->version == node->priv->version, FALSE);

  if (key != NULL)
    *key = item->key;

  if (path != NULL)
    *path = item->path;

  if (value != NULL)
    *value = item->value;

  iter->position = g_list_previous(iter->position);

  return TRUE;
}

COIL_API(void)
coil_struct_merge(CoilStruct  *src,
                  CoilStruct  *dest,
                  gboolean     overwrite,
                  GError     **error)
{
  CoilStructIter it;
  gchar         *key;
  gboolean       different_roots = FALSE;
  GValue        *value, *value_copy, *existing_value = NULL;
  GError        *internal_error = NULL;

  g_return_if_fail(src != NULL);
  g_return_if_fail(COIL_IS_STRUCT(src));
  g_return_if_fail(dest != NULL);
  g_return_if_fail(COIL_IS_STRUCT(dest));
  g_return_if_fail(src != dest);

  if (!coil_is_expanded(src)
    && !coil_struct_expand(src, &internal_error))
    goto error;

  if (coil_struct_is_empty(src))
    return;

  /* XXX: if roots are different then we need a
   * full recursive expand on source
   * also intelligently copy only
   * the real value's from expanded values in the loop below
   */
  if (!coil_struct_has_same_root(src, dest))
  {
    different_roots = TRUE;
    if (!coil_struct_expand_recursive(src, &internal_error))
    goto error;
  }

  coil_struct_iter_init(&it, src);

  while (coil_struct_iter_next(&it, &key, NULL, &value))
  {
    // check if value exists in dest or key is marked deleted
    if (g_hash_table_lookup_extended(dest->priv->key_table, key,
          (gpointer *)NULL, (gpointer *)&existing_value)
        && !overwrite)
    {
      if (existing_value
        && G_VALUE_HOLDS(existing_value, COIL_TYPE_STRUCT)
        && G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
      {
        CoilStruct *_src, *_dest;

        _src  = COIL_STRUCT(g_value_get_object(value));
        _dest = COIL_STRUCT(g_value_get_object(existing_value));

        g_object_freeze_notify(G_OBJECT(_dest));
        coil_struct_merge(_src, _dest, overwrite, &internal_error);
        g_object_thaw_notify(G_OBJECT(_dest));

        g_object_set(G_OBJECT(_dest),
                     "is-prototype",
                     FALSE, NULL);

        if (G_UNLIKELY(internal_error))
          goto error;
      }

      continue;
    }

    if (G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
    {
      CoilStruct *node, *node_copy;
      node = COIL_STRUCT(g_value_dup_object(value));
      node_copy = coil_struct_copy(node, dest, &internal_error);

      if (!node_copy)
      {
        g_object_unref(node);
        goto error;
      }

      g_object_unref(node);
      new_value(value_copy, COIL_TYPE_STRUCT, take_object, node_copy);
    }
    else if (different_roots
        && G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE))
    {
      GValue *real_value;
      if (!coil_expand_value(value, &real_value, &internal_error))
        goto error;
      value_copy = copy_value(real_value);
    }
    else
      value_copy = copy_value(value);

    coil_struct_set_key_value(dest, g_strdup(key), value_copy, &internal_error);

    if (G_UNLIKELY(internal_error))
      goto error;
  }

  return;

error:
  g_assert(internal_error != NULL);
  g_propagate_error(error, internal_error);
}

/* This should not be called directly
 * Call indirectly by coil_struct_expand or coil_expand
 * */
static gboolean
_struct_expand(CoilExpandable *super,
              GHashTable      *_visited,
              GError         **error)
{
  GList             *dep;
  GError            *internal_error = NULL;
  CoilStruct        *self, *parent;
  CoilStructPrivate *priv;

  g_return_val_if_fail(super != NULL, FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(super), FALSE);
  g_return_val_if_fail(_visited != NULL, FALSE);
  g_return_val_if_fail(error == NULL || *error == NULL, FALSE);

  self = COIL_STRUCT(super);
  priv = self->priv;

  g_return_val_if_fail(!self->is_prototype, FALSE);

  if (coil_is_expanded(self))
    return TRUE;

  if (!g_static_mutex_trylock(&priv->expand_lock))
  {
    coil_struct_set_error(error, self,
                "Cycle detected in struct expansion at '%s'.",
                priv->path);

    return FALSE;
  }

  /* Don't notify children of modifications while expanding
   * as the struct is not changing
   */
  g_signal_handlers_block_matched(G_OBJECT(self),
                                  G_SIGNAL_MATCH_FUNC,
                                  struct_signals[MODIFY], 0, NULL,
                                  G_CALLBACK(_struct_expand_notify_cb),
                                  NULL);

  if (priv->expand_ptr == NULL)
    priv->expand_ptr = g_list_last(priv->dependencies);

  for (dep = priv->expand_ptr;
       dep != NULL;
       dep = g_list_previous(dep))
  {
    g_assert(dep != NULL);

    GValue *value;
    value = (GValue *)dep->data;

    g_return_val_if_fail(G_IS_VALUE(value), FALSE);

    if (!G_VALUE_HOLDS(value, COIL_TYPE_STRUCT)
      && !coil_expand_value_internal(value, &value, _visited,
                                     &internal_error))
      goto error;

    if (G_VALUE_HOLDS(value, COIL_TYPE_INCLUDE))
        continue;
    else if (!G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
    {
      // XXX: make sure this branch is even possible...
      coil_struct_set_error(error, self,
        "A struct can only inherit from another struct in '%s'. ",
        priv->path);

      goto error;
    }

    parent = COIL_STRUCT(g_value_dup_object(value));

    if (coil_struct_is_prototype(parent))
    {
      coil_struct_set_error(error, self,
        "dependency struct '%s' is still a prototype"
        "(used or extended but never defined).",
          parent->priv->path);

      goto error;
    }

    if (!coil_is_expanded(parent)
      && !coil_expand(parent, _visited, &internal_error))
      goto error;

    if (parent->priv->size)
    {
      coil_struct_merge(parent, self, FALSE, &internal_error);

      if (G_UNLIKELY(internal_error))
        goto error;
    }

    g_signal_handlers_disconnect_matched(parent,
                                         G_SIGNAL_MATCH_FUNC |
                                         G_SIGNAL_MATCH_DATA,
                                         struct_signals[MODIFY], 0, NULL,
                                         G_CALLBACK(_struct_expand_notify_cb),
                                         self);
    g_object_unref(parent);
  }

  if (!self->remember_deps)
  {
    free_value_list(priv->dependencies);
    priv->dependencies = NULL;
    priv->expand_ptr = NULL;
  }
  else
    priv->expand_ptr = priv->dependencies;

  g_object_set(G_OBJECT(super),
               "expanded", TRUE,
               "real_value", NULL,
               NULL);

  priv->version++;

  g_signal_handlers_unblock_matched(G_OBJECT(self),
                                    G_SIGNAL_MATCH_FUNC,
                                    struct_signals[MODIFY], 0, NULL,
                                    G_CALLBACK(_struct_expand_notify_cb),
                                    NULL);

  g_static_mutex_unlock(&priv->expand_lock);

  return TRUE;

error:
  g_static_mutex_unlock(&priv->expand_lock);

  if (internal_error)
    g_propagate_error(error, internal_error);

  return FALSE;
}

COIL_API(gboolean)
coil_struct_expand_recursive(CoilStruct  *self,
                             GError     **error)
{
  CoilStructIter  it;
  GValue         *value;
  GError         *internal_error = NULL;

  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  if (!coil_struct_expand(self, &internal_error))
    goto fail;

  if (!self->priv->size)
    return TRUE;

  coil_struct_iter_init(&it, self);
  while (coil_struct_iter_next(&it, NULL, NULL, &value))
  {
    if (G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
    {
      coil_struct_expand_recursive(COIL_STRUCT(g_value_get_object(value)),
                                   &internal_error);

      if (G_UNLIKELY(internal_error))
        goto fail;
    }
    else if (G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE)
      && !coil_expand_value(value, NULL, &internal_error))
        goto fail;
  }

  return TRUE;

fail:
  g_assert(internal_error);
  g_propagate_error(error, internal_error);
  return FALSE;
}

COIL_API(gboolean)
coil_struct_expand(CoilStruct *self,
                   GError    **error)
{
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);

  return coil_expand(self, NULL, error);
}

/* Thread safe */
static GValue *
_resolve_path_and_lookup(CoilStruct     *self,
                         const gchar    *path,
                         CoilPathType    lookup_type,
                         gchar          *lookup_buffer,
                         GError        **error)
{
  CoilStructPrivate *priv;
  GHashTable        *table = NULL;
  gboolean           rc = FALSE;

  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);
  g_return_val_if_fail(path != NULL, NULL);
  g_return_val_if_fail(lookup_buffer != NULL, NULL);

  priv = self->priv;

  if (path)
    switch (lookup_type)
    {
      case COIL_PATH:
      case COIL_PATH_RELATIVE:
      case COIL_PATH_ABSOLUTE:
        table = priv->path_table;
        rc = coil_path_resolve_full(priv->path, path,
                                    lookup_buffer, NULL, NULL, error);
        break;

      case COIL_PATH_CONTAINER:
        table = priv->path_table;
        rc = coil_path_resolve_full(priv->path, path,
                                    NULL, lookup_buffer, NULL, error);
        break;

      case COIL_PATH_KEY:
        table = priv->key_table;
        rc = coil_path_resolve_full(priv->path, path,
                                    NULL, NULL, lookup_buffer, error);
        break;

      default:
        g_assert_not_reached();
    }

  g_assert(table);

  return (rc) ? g_hash_table_lookup(table, lookup_buffer) : NULL;
}

static inline GValue *
_maybe_expand_value(GValue *value,
                    GError **error)
{
  if (value == NULL
    || (G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE)
    && !coil_expand_value_internal(value, &value, NULL, error)))
    return NULL;

  return value;
}

/*
 * coil_struct_get_key_value:
 *
 * @self: a CoilStruct instance.
 * @key: the key to get from a struct.
 * @error: a GError pointer or %NULL.
 *
 * Return value: the GValue which corresponds with key in struct.
 *
 */
COIL_API(GValue *)
coil_struct_get_key_value(CoilStruct  *self,
                     const gchar      *key,
                     gboolean          expand_value,
                     GError          **error)
{
  CoilStructPrivate *priv;
  GValue            *result = NULL;
  GError            *internal_error = NULL;

  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);
  g_return_val_if_fail(!self->is_prototype, NULL);
  g_return_val_if_fail(key != NULL, NULL);

  priv = self->priv;

  /* If key is not a value or marked deleted, try to expand */
  if (!g_hash_table_lookup_extended(priv->key_table,
                                    key,
                                    (gpointer *)NULL,
                                    (gpointer *)&result)
    && !coil_is_expanded(self)
    && !coil_struct_expand(self, &internal_error)
    && !(result = g_hash_table_lookup(priv->key_table, key)))
    goto fail;

  return (expand_value) ? _maybe_expand_value(result, error) : result;

fail:
  if (internal_error)
    g_propagate_error(error, internal_error);

  return NULL;
}

/*
 * coil_struct_get_path_value:
 *
 * @self: a CoilStruct instance.
 * @path: the path to get
 * @error: a GError pointer or %NULL
 *
 * Return Value: the that corresponds with path in struct.
 *
 */
COIL_API(GValue *)
coil_struct_get_path_value(CoilStruct  *self,
                           const gchar *path,
                           gboolean     expand_value,
                           GError     **error)
{
  CoilStructPrivate *priv;
  GValue            *result;
  GError            *internal_error = NULL;

  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);
  g_return_val_if_fail(!self->is_prototype, NULL);
  g_return_val_if_fail(path != NULL, NULL);

  priv = self->priv;

  if (COIL_PATH_IS_ABSOLUTE(path)
    && coil_is_expanded(self))
    result = g_hash_table_lookup(priv->path_table, path);
  else
  {
    gchar buffer[COIL_PATH_BUFLEN];
    result = _resolve_path_and_lookup(self, path,
                                      COIL_PATH_ABSOLUTE,
                                      buffer, &internal_error);

    if (G_UNLIKELY(internal_error))
      goto fail;

    if (result == NULL /* REMOVE check below.. we cause 2 lookups */
     && !coil_struct_is_deleted_path(self, buffer)
     && !coil_is_expanded(self))
    {
      if (!coil_struct_expand(self, &internal_error))
        goto fail;

      result = g_hash_table_lookup(priv->path_table, buffer);
    }
  }

  return (expand_value) ? _maybe_expand_value(result, error) : result;

fail:
  if (internal_error)
    g_propagate_error(error, internal_error);

  return NULL;
}

/*
 * coil_struct_contains_key:
 *
 * @self: a CoilStruct instance
 * @key: a key to check for in struct
 *
 * Return Value: TRUE if the key exists in struct, FALSE otherwise.
 *
 * XXX TODO XXX
 */
COIL_API(gboolean)
coil_struct_contains_key(CoilStruct   *self,
                         const gchar  *key,
                         gboolean      check_secondary_keys)
{
  CoilStructPrivate *priv;

  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(!self->is_prototype, FALSE);

  priv = self->priv;

  if (coil_struct_is_empty(self))
    return FALSE;

  if (!check_secondary_keys)
    return g_hash_table_lookup_extended(priv->key_table, key, NULL, NULL);

  // TODO: parent logic...

  return FALSE;
}

/*
 * coil_struct_contains_path:
 * @self: a CoilStruct instance
 * @path: the path to check for
 *
 * Return Value: TRUE if the path exists in the struct's path table
 *              Does NOT check if @path is a subpath of @self
 *
 * XXX TODO XXX
 */
COIL_API(gboolean)
coil_struct_contains_path(CoilStruct   *self,
                          const gchar  *path,
                          gboolean      check_secondary_keys)
{
  g_return_val_if_fail(COIL_IS_STRUCT(self), FALSE);
  g_return_val_if_fail(path != NULL, FALSE);

  CoilStructPrivate *priv;
  GValue            *lookup = NULL;

  priv = self->priv;

  if (coil_struct_is_empty(self))
    return FALSE;

  if (!check_secondary_keys && COIL_PATH_IS_ABSOLUTE(path))
  {
    lookup = g_hash_table_lookup(priv->path_table, path);

    if (lookup != NULL)
    {
      if (G_VALUE_HOLDS(lookup, COIL_TYPE_STRUCT)
        && coil_struct_is_prototype(COIL_STRUCT(g_value_get_object(lookup))))
        return FALSE;

      return TRUE;
    }

    return FALSE;
  }

  gboolean result = FALSE;
  gchar    _path[COIL_PATH_BUFLEN];

  if (coil_path_resolve(priv->path, path, _path, NULL))
    result = (NULL != g_hash_table_lookup(priv->path_table, _path));

  if (!result && check_secondary_keys)
  {
    // TODO::::::::::::::::::::::;
  }

  return result;
}

static GList *
_struct_get_order_items(const CoilStruct *self,
                        StructItemType type)
{
  CoilStructPrivate *priv;
  GList             *order, *list = NULL;
  StructItem         *item;

  g_return_val_if_fail(self != NULL, NULL);
  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);

  if (coil_struct_is_empty(self))
    return NULL;

  priv = self->priv;
  order = priv->order;

  g_assert(order);

  if (type & STRUCT_ITEM_PATH)
    do
    {
      item = (StructItem *)order->data;
      list = g_list_prepend(list, item->path);
    } while ((order = g_list_next(order)));
  else if (type & STRUCT_ITEM_KEY)
    do
    {
      item = (StructItem *)order->data;
      list = g_list_prepend(list, item->key);
    } while ((order = g_list_next(order)));
  else if (type & STRUCT_ITEM_VALUE)
    do
    {
      item = (StructItem *)order->data;
      list = g_list_prepend(list, item->value);
    } while ((order = g_list_next(order)));
  else
      g_assert_not_reached();

  if (!(coil_is_expanded(self)
    || priv->dependencies == NULL))
  {
    const GList  *lp;
    GValue       *dep;
    CoilStruct   *parent;

    if (priv->expand_ptr)
      lp = priv->expand_ptr;
    else
      lp = g_list_last(priv->dependencies);

    do
    {
      dep = (GValue *)lp->data;
      g_assert(G_VALUE_HOLDS(dep, COIL_TYPE_STRUCT));

      parent = COIL_STRUCT(g_value_get_object(dep));
      list = g_list_concat(list, _struct_get_order_items(parent, type));
    } while ((lp = g_list_previous(lp)));
  }

  return list;
}

/*
 * coil_struct_get_keys: get the keys in a CoilStruct
 *
 * @self: A CoilStruct instance.
 *
 * Return Value: a GList of gchar*
 */
COIL_API(GList *)
coil_struct_get_keys(CoilStruct *self)
{
  return _struct_get_order_items(self, STRUCT_ITEM_KEY);
}

/*
 * coil_struct_get_paths: get the paths from a CoilStruct
 *
 * @self: A CoilStruct instance.
 *
 * Return Value: a GList of gchar *
 */
COIL_API(GList *)
coil_struct_get_paths(CoilStruct *self)
{
  return _struct_get_order_items(self, STRUCT_ITEM_PATH);
}

/*
 * coil_struct_get_values: get the values in a CoilStruct
 *
 * @self: A CoilStruct instance.
 *
 * Return Value: a GList of GValue*
 */
COIL_API(GList *)
coil_struct_get_values(CoilStruct *self)
{
  return _struct_get_order_items(self, STRUCT_ITEM_VALUE);
}

/*
 * coil_struct_get_size: get the size of a struct
 *
 * @self: A CoilStruct instance.
 *
 * Return Value: the number of elements in a struct.
 *
 */
COIL_API(guint)
coil_struct_get_size(const CoilStruct *self)
{
  CoilStructPrivate *priv;
  guint              size;

  g_return_val_if_fail(self != NULL, 0);
  g_return_val_if_fail(COIL_IS_STRUCT(self), 0);

  priv = self->priv;
  size = priv->size;

  if (!(coil_is_expanded(self) || priv->dependencies == NULL))
  {
    GList *lp = (priv->expand_ptr) ? priv->expand_ptr
                                   : g_list_last(priv->dependencies);
    do
    {
     GValue *dep = (GValue *)lp->data;

     /*XXX: will fail for later when @file is added
      * the file will have to be loaded but not expand into its dependents */
     g_assert(G_VALUE_HOLDS(dep, COIL_TYPE_STRUCT));
     size += coil_struct_get_size(COIL_STRUCT(g_value_get_object(dep)));
    } while ((lp = g_list_previous(lp)));
  }

  return size;
}

static void
coil_struct_build_string_internal(CoilStruct *self,
                                  GString    *const buffer,
                                  gchar      *prefix,
                                  GError    **error)
{
  CoilStructPrivate *priv;
  CoilStructIter     it;
  gchar             *key;
  GValue            *value;
  GError            *internal_error = NULL;

  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(error == NULL || *error == NULL);
  g_return_if_fail(!self->is_prototype);

  priv = self->priv;

  if (G_UNLIKELY(!prefix
    && !coil_is_expanded(self)
    && !coil_struct_expand(self, &internal_error)))
    goto error;

  if (G_UNLIKELY(!prefix))
    prefix = "";

  coil_struct_iter_init(&it, self);

  while (coil_struct_iter_next(&it, &key, NULL, &value))
  {
    if (G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
    {
      CoilStruct *child = COIL_STRUCT(g_value_get_object(value));

      g_assert(!child->is_prototype);

      if (!coil_is_expanded(child)
        && !coil_struct_expand(child, &internal_error))
        goto error;

      if (!coil_struct_get_size(child))
      {
        g_string_append_printf(buffer, "%s%s: {}", prefix, key);
      }
      else
      {
        gchar *child_prefix = g_strconcat(COIL_BLOCK_PADDING, prefix, NULL);

        g_string_append_printf(buffer, "%s%s: {\n", prefix, key);

        coil_struct_build_string_internal(child,
                                          buffer,
                                          child_prefix,
                                          &internal_error);

        if (G_UNLIKELY(internal_error))
        {
          g_free(child_prefix);
          goto error;
        }

        g_string_append_printf(buffer, "\n%s%c", prefix, '}');

        g_free(child_prefix);
      }
    }
    else
    {
      g_string_append_printf(buffer, "%s%s: ",
                             prefix,
                             key);

      coil_value_build_string(value, buffer, &internal_error);

      if (G_UNLIKELY(internal_error))
        goto error;
    }

    g_string_append_c(buffer, '\n');
  }

  if (buffer->str[buffer->len - 1] == '\n'
    && !coil_struct_is_root(self))
    g_string_truncate(buffer, buffer->len - 1);

  return;

error:
  g_propagate_error(error, internal_error);
}

static void
_struct_build_string(CoilExpandable *self,
                     GString        *const buffer,
                     GError        **error)
{
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(error == NULL || *error == NULL);

  coil_struct_build_string_internal(COIL_STRUCT(self), buffer, NULL, error);
}

/*
 * coil_struct_build_string: Convert a CoilStruct into a string.
 *
 * @self: A CoilStruct instance.
 *
 * @prefix: The string to prefix every line
 *
 * @prefix_len: The length of @prefix.
 *
 * Return Value: The string representation of a CoiLStruct
 *
 */
COIL_API(void)
coil_struct_build_string(CoilStruct *self,
                         GString    *const buffer,
                         GError    **error)
{
  g_return_if_fail(COIL_IS_STRUCT(self));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(error == NULL || *error == NULL);

  coil_struct_build_string_internal(self, buffer, NULL, error);
}

COIL_API(gchar *)
coil_struct_to_string(CoilStruct *self,
                      GError    **error)
{
  GString *buffer;

  g_return_val_if_fail(self != NULL, NULL);
  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);
  g_return_val_if_fail(error == NULL || *error == NULL, NULL);

  /* short circuit */
  if (coil_struct_is_empty(self) && !coil_struct_get_size(self))
    return g_strndup(COIL_STATIC_STRLEN("{}"));

  buffer = g_string_sized_new(512);
  coil_struct_build_string_internal(self, buffer, NULL, error);

  return g_string_free(buffer, FALSE);
}

/*
 * coil_struct_copy: Deep copy for CoilStruct objects.
 *
 * @self: The CoilStruct to copy
 *
 * @container: The container for the copy
 *
 * Return Value: A CoilStruct copy of @self
 *
 */
COIL_API(CoilStruct *)
coil_struct_copy(CoilStruct       *self,
                 const CoilStruct *new_container,
                 GError          **error)
{
  CoilStruct        *copy;
  CoilStructPrivate *priv;
  CoilExpandable    *super;
  GError            *internal_error = NULL;

  g_return_val_if_fail(COIL_IS_STRUCT(self), NULL);
  g_return_val_if_fail(!self->is_prototype, NULL);
  g_return_val_if_fail(new_container == NULL
                  || COIL_IS_STRUCT(new_container), NULL);

  g_return_val_if_fail(self != new_container, NULL);

  priv  = self->priv;
  super = COIL_EXPANDABLE(self);
  copy  = coil_struct_new("name", priv->name,
                          "container", new_container,
                          "location", &super->location,
                          "doc", self->doc);

  /* if no new_container then copy is @root
   * so we'll want to expand, not copy deps
   * XXX: potential expand errors are silenced here
   * may consider adding error passing to this function for that
   * visibility.
   */
  if (new_container == NULL
    || (coil_struct_get_root(new_container) != coil_struct_get_root(self)
    && !coil_struct_expand_recursive(self, &internal_error)))
  {
    g_propagate_error(error, internal_error);
    return NULL;
  }
  else if (priv->dependencies)
  {
    const GList *link;
    link = g_list_last(priv->dependencies);
    do
    {
      GValue *dep = (GValue *)link->data;
      coil_struct_add_dependency(copy, G_VALUE_TYPE(dep),
                            (gpointer)g_value_get_object(dep));
      link = g_list_previous(link);
    } while (link != NULL);
  }

  if (!coil_struct_is_empty(self))
  {
    CoilStructIter  it;
    gchar          *key;
    GValue         *value, *value_copy;

    /* iterate keys in order */
    coil_struct_iter_init(&it, self);

    while (coil_struct_iter_next(&it, &key, NULL, &value))
    {
      if (value == NULL)
      {
        coil_struct_mark_key_deleted(copy, g_strdup(key), NULL);
        continue;
      }

      if (G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
      {
        CoilStruct *node, *node_copy;
        node  = COIL_STRUCT(g_value_dup_object(value));
        node_copy = coil_struct_copy(node, copy, &internal_error);

        if (!node_copy)
        {
          g_object_unref(node);
          g_propagate_error(error, internal_error);
          return NULL;
        }

        g_object_unref(node);
        new_value(value_copy, COIL_TYPE_STRUCT, take_object, node_copy);
      }
      else
        value_copy = copy_value(value);

      coil_struct_set_key_value(copy, g_strdup(key), value_copy, &internal_error);

      if (G_UNLIKELY(internal_error))
      {
        g_propagate_error(error, internal_error);
        return NULL;
      }
    }
  }

  return copy;
}

static gint
_struct_item_cmp(const StructItem *n1,
                 const StructItem *n2)

{
  return strcmp(n1->key, n2->key);
}

COIL_API(gboolean)
coil_struct_equals(gconstpointer e1,
                   gconstpointer e2,
                   GError        **error)
{
  CoilStructPrivate  *p1, *p2;
  CoilStruct         *s1, *s2;
  register GList     *lp1 = NULL, *lp2 = NULL;
  GError             *internal_error = NULL;

  if (e1 == e2)
    return TRUE;

  g_return_val_if_fail(COIL_IS_STRUCT(e1), FALSE);
  g_return_val_if_fail(COIL_IS_STRUCT(e2), FALSE);

  s1 = COIL_STRUCT(e1);
  s2 = COIL_STRUCT(e2);

  if (s1 == s2)
    return TRUE;

  if (coil_struct_is_descendent(s1, s2)
    || coil_struct_is_descendent(s2, s1))
    return FALSE;

  p1 = s1->priv;
  p2 = s2->priv;

  if (!coil_struct_expand_recursive(s1, &internal_error)
    || !coil_struct_expand_recursive(s2, &internal_error)
    || p1->size != p2->size
    || g_list_length(p1->order) != g_list_length(p2->order))
    goto fail;

  // All keys are first-order ok to sort
  lp1 = g_list_sort(g_list_copy(p1->order), (GCompareFunc)_struct_item_cmp);
  lp2 = g_list_sort(g_list_copy(p2->order), (GCompareFunc)_struct_item_cmp);

  // Loop foreach equal key
  while (lp1 && lp2)
  {
    StructItem *i1, *i2;
    GValue *v1, *v2;

    i1 = (StructItem *)lp1->data;
    i2 = (StructItem *)lp2->data;

    // compare keys
    if (strcmp(i1->key, i2->key) != 0)
      goto fail;

    v1 = i1->value;
    v2 = i2->value;

    if (v1 != v2)
    {
      if ((v1 == NULL || v2 == NULL)
        || (G_VALUE_HOLDS(v1, COIL_TYPE_EXPANDABLE)
          && !coil_expand_value(v1, &v1, &internal_error))
        || (G_VALUE_HOLDS(v2, COIL_TYPE_EXPANDABLE)
          && !coil_expand_value(v2, &v2, &internal_error)))
        goto fail;

      if (G_VALUE_HOLDS(v1, COIL_TYPE_STRUCT)
        && G_VALUE_HOLDS(v2, COIL_TYPE_STRUCT))
      {
        if (!coil_struct_equals(g_value_get_object(v1),
                                g_value_get_object(v2),
                                &internal_error))
          goto fail;
      }
      else if (coil_value_compare(v1, v2, &internal_error) != 0)
        goto fail;
    }

    lp1 = g_list_delete_link(lp1, lp1);
    lp2 = g_list_delete_link(lp2, lp2);
  }

  g_assert(lp1 == NULL && lp1 == lp2);

  return TRUE;

fail:
  if (lp1)
    g_list_free(lp1);

  if (lp2)
    g_list_free(lp2);

  if (internal_error)
    g_propagate_error(error, internal_error);

  return FALSE;
}

/*
 * coil_struct_class_init: Class initializer for CoilStruct
 *
 * @klass: A CoilStructClass
 */
static void
coil_struct_class_init (CoilStructClass *klass)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (klass);

  g_type_class_add_private(klass, sizeof(CoilStructPrivate));

  /* GObject class methods */
  gobject_class->constructor  = coil_struct_constructor;
  gobject_class->set_property = coil_struct_set_property;
  gobject_class->get_property = coil_struct_get_property;
  gobject_class->finalize     = coil_struct_finalize;

   /* override expandable methods */
  CoilExpandableClass *expandable_class = COIL_EXPANDABLE_CLASS(klass);
  expandable_class->expand              = _struct_expand;
  expandable_class->equals              = coil_struct_equals;
  expandable_class->build_string        = _struct_build_string;

  /* setup param specifications */

  g_object_class_install_property(gobject_class, PROP_NAME,
          g_param_spec_string("name",
                              "set the unqualified name of this struct.",
                              "set/get the unqualified name of this struct.",
                              COIL_ROOT_PATH,
                              G_PARAM_CONSTRUCT |
                              G_PARAM_READWRITE));

  g_object_class_install_property(gobject_class, PROP_DOC,
          g_param_spec_string("doc",
                              "The documentation string for this struct.",
                              "get/set the doc string for this struct.",
                              NULL,
                              G_PARAM_CONSTRUCT |
                              G_PARAM_READWRITE));

  g_object_class_install_property(gobject_class, PROP_ALWAYS_EXPAND,
          g_param_spec_boolean("always_expand",
                               "If TRUE all expandables are always expanded"
                               " as they are added",
                               "get/set always_expand",
                               FALSE,
                               G_PARAM_CONSTRUCT |
                               G_PARAM_READWRITE));

  g_object_class_install_property(gobject_class, PROP_IS_PROTOTYPE,
          g_param_spec_boolean("is-prototype",
                               "",
                               "",
                               FALSE,
                               G_PARAM_READWRITE |
                               G_PARAM_CONSTRUCT));


  g_object_class_install_property(gobject_class, PROP_PATH,
          g_param_spec_string("path",
                              "The path of this struct.",
                              "get/set the path of this struct.",
                              NULL,
                              G_PARAM_READWRITE));

  struct_signals[CREATE] =
    g_signal_newv("create",
                  G_TYPE_FROM_CLASS(klass),
                  G_SIGNAL_DETAILED,
                  NULL, NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE, 0, NULL);

  struct_signals[MODIFY] =
    g_signal_newv("modify",
                 G_TYPE_FROM_CLASS(klass),
                 G_SIGNAL_NO_RECURSE,
                 NULL, NULL, NULL,
                 coil_cclosure_marshal_POINTER__VOID,
                 G_TYPE_POINTER, 0, NULL);

  struct_signals[DESTROY] =
    g_signal_newv("destroy",
                 G_TYPE_FROM_CLASS(klass),
                 G_SIGNAL_NO_RECURSE,
                 NULL, NULL, NULL,
                 coil_cclosure_marshal_POINTER__VOID,
                 G_TYPE_POINTER, 0, NULL);
}

