/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

G_DEFINE_TYPE(CoilInclude, coil_include, COIL_TYPE_EXPANDABLE);

#define COIL_INCLUDE_GET_PRIVATE(obj)                                         \
        (G_TYPE_INSTANCE_GET_PRIVATE((obj), COIL_TYPE_INCLUDE,                \
         CoilIncludePrivate))

struct _CoilIncludePrivate
{
  GValue *include_path_value;
  gchar  *include_path;
  GList  *import_list;
};

typedef enum
{
  PROP_0,
  /**/
  PROP_INCLUDE_PATH,
  PROP_INCLUDE_PATH_VALUE,
  PROP_IMPORT_LIST,
} CoilIncludeProperties;

#ifdef COIL_INCLUDE_CACHING

static GHashTable *open_files = NULL;

typedef struct _include_cache_rec include_cache_rec;

struct _include_cache_rec
{
  gchar        *filepath;
  CoilStruct   *cacheable;
  time_t        m_time;
  volatile gint ref_count;
};

static void
include_cache_init(void)
{
  if (open_files == NULL)
    open_files = g_hash_table_new_full(coil_str_hash, g_str_equal,
                                       NULL, NULL);
}

static void
_include_cache_delete_rec(include_cache_rec *rec)
{
  g_hash_table_remove(open_files, rec->filepath);
  g_object_unref(rec->cacheable);
  g_free(rec->filepath);
  g_free(rec);
}

static CoilStruct *
include_cache_lookup(const gchar *filepath,
                     GError     **error)
{
  include_cache_rec *rec;

  g_return_val_if_fail(filepath != NULL, NULL);

  if ((rec = g_hash_table_lookup(open_files, filepath)))
  {
    struct stat buf;

    if (stat(filepath, &buf) == 0
      && buf.st_mtime != rec->m_time)
    {
      CoilStruct *_root;

      /* re-cache file */
      if (!(_root = coil_parse_file(filepath, error)))
      {
        _include_cache_delete_rec(rec);
        return NULL;
      }

      g_object_unref(rec->cacheable);
      rec->cacheable = _root;
      rec->m_time = buf.st_mtime;
    }

    return rec->cacheable;
  }

  return NULL;
}

static void
_include_cache_gc_notify(gpointer data, GObject *addr)
{
  gchar             *filepath;
  include_cache_rec *rec;

  g_return_if_fail(data != NULL);
  g_return_if_fail(G_IS_OBJECT(addr));

  filepath = (gchar *)data;
  rec = g_hash_table_lookup(open_files, filepath);
  g_return_if_fail(rec != NULL);

  if (g_atomic_int_dec_and_test(&rec->ref_count))
    _include_cache_delete_rec(rec);
}

static void
include_cache_save(CoilStruct  *root,
                   const gchar *filepath,
                   CoilStruct  *cacheable)
{
  include_cache_rec *rec;

  g_return_if_fail(COIL_IS_STRUCT(root));
  g_return_if_fail(filepath != NULL);
  g_return_if_fail(COIL_IS_STRUCT(cacheable));

  if ((rec = g_hash_table_lookup(open_files, filepath)) != NULL)
    g_atomic_int_inc(&rec->ref_count);
  else
  {
    rec = g_new(include_cache_rec, 1);
    rec->ref_count = 1;
    rec->filepath = g_strdup(filepath);
    rec->cacheable = g_object_ref(cacheable);

    {
      struct stat buf;
      if (stat(filepath, &buf) == 0)
        rec->m_time = buf.st_mtime;
      else
        rec->m_time = (time_t)0;
    }

    g_hash_table_insert(open_files, rec->filepath, rec);
  }

  g_object_weak_ref(G_OBJECT(root),
                    (GWeakNotify)_include_cache_gc_notify,
                    (gpointer)rec->filepath);
}

#endif

static GObject *
coil_include_constructor(GType                  gtype,
                         guint                  n_properties,
                         GObjectConstructParam *properties)
{
  GObjectClass *object_class  = G_OBJECT_CLASS(coil_include_parent_class);
  GObject      *object        = object_class->constructor(gtype,
                                                          n_properties,
                                                          properties);

  CoilInclude        *self = COIL_INCLUDE(object);
  CoilIncludePrivate *priv = self->priv;

  if (n_properties < 2
      && !(n_properties == 1
      && priv->import_list == NULL))
    g_error("Include path must be specified.");

  return object;
}

static void
coil_include_finalize(GObject *object)
{
  CoilInclude        *self;
  CoilIncludePrivate *priv;

  self = COIL_INCLUDE(object);
  priv = self->priv;

  if (priv->include_path_value)
    free_value(priv->include_path_value);

  if (priv->include_path)
    g_free(priv->include_path);

  if (priv->import_list)
    free_value_list(priv->import_list);

  G_OBJECT_CLASS(coil_include_parent_class)->finalize(object);
}

static void
coil_include_set_property(GObject      *object,
                          guint         property_id,
                          const GValue *value,
                          GParamSpec   *pspec)
{
  CoilInclude        *self;
  CoilIncludePrivate *priv;

  self = COIL_INCLUDE(object);
  priv = self->priv;

  switch (property_id)
  {
    case PROP_INCLUDE_PATH:
      priv->include_path = g_value_dup_string(value);
      break;

    /* XXX: steals value pointer */
    case PROP_INCLUDE_PATH_VALUE:
      priv->include_path_value = (GValue *)g_value_get_pointer(value);
      break;

    /* XXX: steals list pointer */
    case PROP_IMPORT_LIST:
      priv->import_list = (GList *)g_value_get_pointer(value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property_id, pspec);
      break;
  }
}

static void
coil_include_init(CoilInclude *self)
{
  CoilIncludePrivate *priv;

  priv = COIL_INCLUDE_GET_PRIVATE(self);

  self->priv               = priv;
  priv->import_list        = NULL;
  priv->include_path       = NULL;
  priv->include_path_value = NULL;
}

static gboolean
_include_expand(CoilExpandable *super,
                GHashTable     *_visited,
                GError        **error)
{
  CoilInclude        *self;
  CoilIncludePrivate *priv;
  CoilStruct         *_root = NULL;
  gchar              *include_path;
  GError             *internal_error = NULL;

  g_return_val_if_fail(COIL_IS_INCLUDE(super), FALSE);
  g_return_val_if_fail(_visited != NULL, FALSE);
  g_return_val_if_fail(error == NULL || *error == NULL, FALSE);

  self = COIL_INCLUDE(super);
  priv = self->priv;

  if (!priv->include_path)
  {
    g_assert(priv->include_path_value);
    GValue *value = priv->include_path_value;

    if (G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE)
      && !coil_expand_value_internal(value, &value,
                                     NULL, &internal_error))
      goto error;

    if (!G_VALUE_HOLDS(value, G_TYPE_STRING))
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_FILE,
                  "@file include path must be a string or "
                  "string expression which must resolve to a string.");

      goto error;
    }

    include_path = (gchar *)g_value_get_string(value);
  }
  else
    include_path = priv->include_path;

  g_assert(include_path);
  g_strstrip(include_path);

  if (super->location.filepath)
  {
    const gchar *this_filepath = super->location.filepath;

    if (G_UNLIKELY(strcmp(include_path, this_filepath) == 0))
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_FILE,
                  "@file cannot import from the same"
                  " file that it is contained in.");

      goto error;
    }

    if (!g_path_is_absolute(include_path))
    {
      gchar *dirname;

      dirname = g_path_get_dirname(this_filepath);
      include_path = g_build_filename(dirname, include_path, NULL);
      g_free(dirname);

      if (priv->include_path)
        g_free(priv->include_path);

      priv->include_path = include_path;
    }
  }

#ifdef COIL_INCLUDE_CACHING
  if ((_root = include_cache_lookup(include_path, &internal_error)))
    g_object_ref(_root);
  else if (G_UNLIKELY(internal_error))
    goto error;
  else
#endif
  if (G_UNLIKELY(!g_file_test(include_path,
                              G_FILE_TEST_IS_REGULAR |
                              G_FILE_TEST_EXISTS)))
  {
    g_set_error(error,
                COIL_ERROR,
                COIL_ERROR_FILE,
                "@file include path '%s' does not exist.",
                include_path);

    goto error;
  }
  else if (!(_root = coil_parse_file(include_path, &internal_error)))
    goto error;

  g_assert(_root != NULL);

#ifdef COIL_INCLUDE_CACHING
  include_cache_save(coil_struct_get_root(super->container),
                     include_path, _root);
#endif

  if (priv->import_list
      && g_list_length(priv->import_list) != coil_struct_get_size(_root))
  {
    const GList *lp;
    const gchar *import_path;
    CoilStruct  *import_struct;
    guint        arg_num = 2;

    lp = priv->import_list;

    do
    {
      GValue *value = (GValue *)lp->data;

      if (G_VALUE_HOLDS(value, COIL_TYPE_EXPANDABLE)
        && !coil_expand_value_internal(value, &value,
                                       NULL, &internal_error))
        goto error;

#if 0 /* TODO: after expressions are added */
      if (G_VALUE_HOLDS(value, COIL_TYPE_EXPRESSION)
        && !coil_expand_value_internal(value, &value, NULL, &internal_error)
        goto error;

      if (G_VALUE_HOLDS(value, COIL_TYPE_LIST))
      {
        /* pseudo: ..
         * stringify list
         * iterate list
         * use g_list_insert_before to inject into main loop
         */
      }

#endif

      if (!G_VALUE_HOLDS(value, G_TYPE_STRING))
      {
        g_set_error(error,
                    COIL_ERROR,
                    COIL_ERROR_FILE,
                    "@file sub-import argument %d must resolve to a string.",
                    arg_num);

        goto error;
      }

      import_path = (gchar *)g_value_get_string(value);

#if 0 /* XXX: reflect changes in loop structure if this code is enabled */
        if (!preserve_deps)
        {
         free_value(value);
         lp = g_list_delete_link(lp, lp);
        }
      value = NULL;
#endif

      if (!(value = coil_struct_get_path_value(_root, import_path, TRUE,
                                               &internal_error)))
        goto error;

      if (!G_VALUE_HOLDS(value, COIL_TYPE_STRUCT))
      {
        g_set_error(error,
                    COIL_ERROR,
                    COIL_ERROR_FILE,
                    "@file sub-import argument %d ('%s') "
                    "must resolve to a Struct in file %s.",
                    arg_num, import_path, include_path);

        goto error;
      }

      import_struct = COIL_STRUCT(g_value_dup_object(value));

      /* XXX: Copy directly to target container
       */
      coil_struct_merge(import_struct, super->container,
                        FALSE, &internal_error);

      g_object_unref(import_struct);

      if (G_UNLIKELY(internal_error))
        goto error;

     arg_num++;
    } while ((lp = g_list_next(lp)));
  }
  else
  {
    coil_struct_merge(_root, super->container, FALSE, &internal_error);
    if (G_UNLIKELY(internal_error))
        goto error;
  }

  g_object_set(G_OBJECT(super),
               "expanded", TRUE,
               "real_value", NULL,
               NULL);

  g_object_unref(_root);

  return TRUE;

error:
  if (_root != NULL)
    g_object_unref(_root);

  if (internal_error)
    g_propagate_error(error, internal_error);

  return FALSE;
}

COIL_API(gboolean)
coil_include_equals(gconstpointer   e1,
                    gconstpointer   e2,
                    GError        **error)
{
  COIL_NOT_IMPLEMENTED(FALSE);
}

static void
_include_build_string(CoilExpandable *self,
                      GString        *const buffer,
                      GError        **error)
{
  g_return_if_fail(COIL_IS_INCLUDE(self));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(error == NULL || *error == NULL);

  coil_include_build_string(COIL_INCLUDE(self), buffer, error);
}

COIL_API(void)
coil_include_build_string(CoilInclude *self,
                          GString     *const buffer,
                          GError     **error)
{
  const CoilIncludePrivate *priv;
  GError                   *internal_error = NULL;

  g_return_if_fail(COIL_IS_INCLUDE(self));
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(error == NULL || *error == NULL);

  priv = self->priv;

  g_string_append_len(buffer, COIL_STATIC_STRLEN("@file: "));

  if (priv->import_list)
    g_string_append_len(buffer, COIL_STATIC_STRLEN("[ "));

  if (priv->include_path)
    g_string_append_printf(buffer, "'%s'", priv->include_path);
  else
  {
    coil_value_build_string(priv->include_path_value, buffer, &internal_error);

    if (G_UNLIKELY(internal_error))
      goto error;
  }

  if (priv->import_list)
  {
    register const GList *lp;
    for (lp = priv->import_list;
         lp != NULL;
         lp = g_list_next(lp))
    {
      coil_value_build_string((GValue *)lp->data, buffer, &internal_error);

      if (G_UNLIKELY(internal_error))
        goto error;

      g_string_append_c(buffer, ' ');
    }

    g_string_append_len(buffer, COIL_STATIC_STRLEN(" ]"));
  }

  return;

error:
  g_propagate_error(error, internal_error);
}

COIL_API(gchar *)
coil_include_to_string(CoilInclude *self,
                       GError     **error)
{
  GString *buffer;

  g_return_val_if_fail(COIL_IS_INCLUDE(self), NULL);
  g_return_val_if_fail(error == NULL || *error == NULL, NULL);

  buffer = g_string_sized_new(128);
  coil_include_build_string(self, buffer, error);

  return g_string_free(buffer, FALSE);
}

static void
coil_include_class_init(CoilIncludeClass *klass)
{
  g_type_class_add_private(klass, sizeof(CoilIncludePrivate));

  GObjectClass *gobject_class = G_OBJECT_CLASS(klass);

  gobject_class->constructor  = coil_include_constructor;
  gobject_class->set_property = coil_include_set_property;
  gobject_class->finalize     = coil_include_finalize;

  CoilExpandableClass *expandable_class = COIL_EXPANDABLE_CLASS(klass);

  expandable_class->expand       = _include_expand;
  expandable_class->equals       = coil_include_equals;
  expandable_class->build_string = _include_build_string;

  g_object_class_install_property(gobject_class, PROP_INCLUDE_PATH,
         g_param_spec_string("include_path",
                             "include_path",
                             "Include path string",
                             NULL,
                             G_PARAM_WRITABLE |
                             G_PARAM_CONSTRUCT_ONLY));

  g_object_class_install_property(gobject_class, PROP_INCLUDE_PATH_VALUE,
         g_param_spec_pointer("include_path_value",
                              "include_path_value",
                              "A value that will resolve to a file path.",
                              G_PARAM_WRITABLE |
                              G_PARAM_CONSTRUCT_ONLY));

  g_object_class_install_property(gobject_class, PROP_IMPORT_LIST,
         g_param_spec_pointer("import_list",
                              "import_list",
                              "A list of paths to process during expansion",
                              G_PARAM_WRITABLE |
                              G_PARAM_CONSTRUCT_ONLY));

#ifdef COIL_INCLUDE_CACHING
  include_cache_init();
#endif

}

