/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

/*
 * Builds a path based on a variable number of key arguments
 *
 * Most code borrowed from g_strconcat
 *
 * @param base the first key in the path
 * @return A valid coil path string assuming the keys are valid
 */
COIL_API(gchar *)
coil_path_build(const gchar *base, ...)
{
  gsize   len;
  va_list args;
  gchar   *buffer, *s, *p;

  if (!base)
    return NULL;

  len = strlen(base);
  va_start(args, base);
  s = va_arg(args, gchar *);
  while (s)
  {
    len += strlen(s) + 1;
    s = va_arg(args, gchar *);
  }
  va_end(args);

  g_assert(len <= COIL_PATH_LEN);

  buffer = g_new(gchar, len + 1);
  p = g_stpcpy(buffer, base);

  va_start(args, base);
  s = va_arg(args, gchar *);
  while (s)
  {
    *p++ = COIL_PATH_DELIM;
    p = g_stpcpy(p, s);
    s = va_arg(args, gchar *);
  }
  va_end(args);

  return buffer;
}

/**
 * Constructs a path inside of a pre-allocated buffer based on keys.
 *
 * @param pre-allocated string buffer to populate
 * @param the first key in path
 * @return a valid path assuming key arguments are valid
 */
COIL_API(void)
coil_path_build_buffer(gpointer buffer,
                       gchar *base, ...)
{
  gchar  *s, *p;
  va_list args;

  if (!base || !buffer)
    return;

  p = g_stpcpy(buffer, base);
  va_start(args, base);
  s = va_arg(args, gchar *);
  while (s)
  {
    *p++ = COIL_PATH_DELIM;
    p = g_stpcpy(p, s);
    s = va_arg(args, gchar *);
  }
  va_end(args);
}

/**
 * Get the container path from a path.
 *
 * @param a coil path string
 * @return the container path string
 */
COIL_API(gchar *)
coil_path_get_container(const gchar *path)
{
  const gchar *offset;

  g_return_val_if_fail(path != NULL, NULL);

  offset = strrchr(path, COIL_PATH_DELIM);

  if (offset == NULL)
    return NULL;

  return g_strndup(path, offset - path);
}

/**
 * Get the key from a path.
 *
 * @param a coil path string
 * @return the key from a path
 */
COIL_API(gchar *)
coil_path_get_key(const gchar *path)
{
  const gchar *key;

  g_return_val_if_fail(path != NULL, NULL);
  g_return_val_if_fail(*path, NULL);

  key = strrchr(path, COIL_PATH_DELIM);

  if (key == NULL)
    key = path;
  else if (!*++key)
    return NULL;

  return g_strdup(key);
}

/**
 * Check that a path is valid
 *
 * @param a coil path string
 * @return TRUE if path is valid.
 */
COIL_API(gboolean)
coil_validate_path(const gchar *path)
{
  static GRegex *path_regex = NULL;

  g_return_val_if_fail(path != NULL, FALSE);

  if (G_UNLIKELY(!path_regex))
  {
    path_regex = g_regex_new("^"COIL_PATH_REGEX"$",
                             G_REGEX_OPTIMIZE,
                             G_REGEX_MATCH_NOTEMPTY,
                             NULL);
  }

  return g_regex_match(path_regex, path, 0, NULL);
}

/**
 * Check that a key is valid
 *
 * @param a coil key string
 * @return TRUE if key is valid
 */
COIL_API(gboolean)
coil_validate_key(const gchar *key)
{
  static GRegex *key_regex = NULL;

  g_return_val_if_fail(key != NULL, FALSE);

  if (G_UNLIKELY(!key_regex))
  {
    key_regex = g_regex_new("^"COIL_KEY_REGEX"$",
                            G_REGEX_OPTIMIZE,
                            G_REGEX_MATCH_NOTEMPTY,
                            NULL);
  }

  return g_regex_match(key_regex, key, 0, NULL);
}

/**
 * Resolve relative path references against an absolute path.
 *
 * If reference is an absolute path no resolution is required.
 * Though, non-null buffers are still populated.
 *
 * Otherwise, compute the results based on an absolute path
 * <i>base</i> and a relative path <i>reference</i> which may contain
 * back-references.
 *
 * Resolution is done in up to 3 unique pre-allocated buffers specified
 * as arguments which are modified t!o contain the fully resolved absolute
 * <i>path</i>, the absolute path of the <i>container</i>, and the
 * <i>key</i> respectively.
 *
 * If you need to store the result on the heap use g_strdup or the like..
 * if the return value was a heap pointer we would do the same thing
 * internally as at least one buffer is required.
 * Passing buffers here prevents library functions from having to
 * repeatedly alloc and free memory solely for lookup purposes. This should
 * really cut down the amount of calls to malloc.
 *
 * I have tried to make this function as fast as possible as it is the
 * corner stone of just about every internal function.
 *
 * Note: Buffers should be large enough to hold COIL_PATH_LEN + 1
 *
 * Example usage:
 *
 * gchar *some_container = "@root.a.b.c"
 * gchar *some_reference = "....x.y.z"
 *
 * gchar key[COIL_PATH_LEN + 1];
 * gchar path[COIL_PATH_LEN + 1];
 * gchar container[COIL_PATH_LEN + 1];
 *
 * GError *path_error = NULL;
 *
 *
 * coil_path_resolve_full(some_container, some_path,
 *                       &path, &container, &key, // buffers
 *                        &path_error);
 *
 * if (path_error)
 * {
 *    g_propagate_error(error, path_error);
 *    return ...
 * }
 *
 * // path = "@root.x.y.z"
 * // container = "@root.x.y"
 * // key = "y"
 *
 * or if you only need some of the values pass NULL ...
 *
 * coil_path_resolve(some_container, some_path,
 *                  NULL, &container, &key,
 *                  &path_error);
 *
 * @param An absolute path to use for the base
 * @param the relative path reference to resolve
 * @param pre-allocated buffer for the result absolute path or NULL
 * @param pre-allocated buffer for the result absolute container path or NULL
 * @param pre-allocated buffer for the result key or NULL
 * @param GError or NULL
 * @return TRUE if path is valid and can be resolved. FALSE otherwise.
 */
COIL_API(gboolean)
coil_path_resolve_full(const gchar *base,
                       const gchar *reference,
                       gchar       *path,
                       gchar       *container,
                       gchar       *key,
                       GError     **error)
{
  g_return_val_if_fail(reference != NULL, FALSE);
  g_return_val_if_fail(!(path == NULL
                    && container == NULL
                    && key == NULL), FALSE);

  if (COIL_PATH_IS_ABSOLUTE(reference))
  {
    if (strlen(reference) == COIL_ROOT_PATH_LEN)
    {
      if (path != NULL)
        strncpy(path, COIL_ROOT_PATH, COIL_ROOT_PATH_LEN);

      if (container != NULL)
        strncpy(container, COIL_ROOT_PATH, COIL_ROOT_PATH_LEN);

      if (key != NULL)
        *key = '\0';

      return TRUE;
    }

    gchar *key_ptr = strrchr(reference + COIL_ROOT_PATH_LEN,
                             COIL_PATH_DELIM);

    if (key_ptr && ++key_ptr
      && *key_ptr != COIL_PATH_DELIM
      && *key_ptr != '\0')
    {
      /* @root(.key)+ */
      if (path != NULL)
        strncpy(path, reference, COIL_PATH_LEN);

      if (container != NULL)
      {
        guint n = key_ptr - reference - 1;
        strncpy(container, reference, n);
        container[n] = '\0';
      }

      if (key != NULL)
        strcpy(key, key_ptr);

      return TRUE;
    }

    /* must be something like @rootasdf or @root. */
    g_set_error(error,
                COIL_ERROR,
                COIL_ERROR_PATH,
                "'%s' is an invalid absolute path. See documentation "
                "for the correct format.",
                reference);

    goto error;
  }
  else
  {
    g_return_val_if_fail(base != NULL, FALSE);

    register const gchar *s, *e;

    s = reference;
    e = base + strlen(base);

    if (*s == COIL_PATH_DELIM)
    {
      while (*++s == COIL_PATH_DELIM)
        while (*--e != COIL_PATH_DELIM && G_LIKELY(e > base))
          /* iterate keys off the end */ ;
    }

    /* check the rest of the path for mid-path references */

    if (strstr(s + 1, COIL_PATH_DELIM_S COIL_PATH_DELIM_S))
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_PATH,
                  "Mid-path references ie. '..' in '%s' "
                  "are not allowed.",
                  reference);

      goto error;
    }

    guint l1, l2;
    guint path_len;

    l1       = e - base; /* base length */
    l2       = strlen(s); /* extra keys */
    path_len = l1 + l2 + 1; /* path length */

    if (G_UNLIKELY(path_len > COIL_PATH_LEN))
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_PATH,
                  "Path length was too long (%d) when resolving '%s' "
                  " against '%s'. A path can contain a maxiumum "
                  "of %d characters.",
                  path_len, reference, base, COIL_PATH_LEN);

      goto error;
    }
    else if (G_UNLIKELY(!l1)) /* really when l1 <= COIL_ROOT_PATH_LEN */
    {
      g_set_error(error,
                  COIL_ERROR,
                  COIL_ERROR_PATH,
                  "Path contains a reference past root while "
                  "attempting to resolve '%s' against '%s'.",
                  reference, base);

      goto error;
    }
    else if (G_UNLIKELY(!l2))
    {
      g_set_error_literal(error,
                          COIL_ERROR,
                          COIL_ERROR_PATH,
                          "References must contain at least one key "
                          "ie '..a'. Where as '..', '...', "
                          "etc are not aloud.");

      goto error;
    }

    gchar *buffer, *p;

    if (path != NULL)
      buffer = path;
    else
      buffer = (gchar *)g_alloca(COIL_PATH_BUFLEN);

    g_assert(buffer != NULL);

    p = buffer;
    memcpy(p, base, l1);
    p += l1;
    *p++ = COIL_PATH_DELIM;
    memcpy(p, s, l2);
    p += l2;
    *p = '\0';

    if (container != NULL
      || key != NULL)
    {
      register const gchar *key_ptr = buffer + path_len;

      while (*key_ptr != COIL_PATH_DELIM)
           key_ptr--;

      g_assert(key_ptr);

      if (container != NULL)
      {
        guint n = key_ptr - buffer;
        strncpy(container, buffer, n);
        container[n] = '\0';
      }

      if (key != NULL)
        strcpy(key, key_ptr + 1);
    }
  }

  return TRUE;

error:

  if (key != NULL)
    *key = '\0';

  if (path != NULL)
    *path = '\0';

  if (container != NULL)
    *container = '\0';

  g_assert(error == NULL || *error != NULL);

  return FALSE;
}

/**
 * Resolves a relative path reference against an absolute path.
 *
 * @param An absolute path to use for the base
 * @param the relative path reference to resolve
 * @param pre-allocated buffer for the result absolute path or NULL
 * @param GError or NULL
 * @return TRUE if path is valid and can be resolved. FALSE otherwise.
 */
COIL_API(gboolean)
coil_path_resolve(const gchar *base,
                  const gchar *reference,
                  gchar       *path,
                  GError     **error)
{
  return coil_path_resolve_full(base, reference, path, NULL, NULL, error);
}

/*
 * Compute the relative path from two absolute paths.
 *
 * This function takes two absolute paths and computes the optimal
 * relative path to reach the second given the first. Where <i>path</i> is
 * the destination and <i>base</i> is the source.
 *
 * Example output:
 *
 * base: @root.asdf.bxd          (*p1)
 * path: @root.asdf.bhd.xxx.yyy  (*p2)
 * result: ..bhd.xxx.yyy
 *
 *
 * base: @root.asdf.bxd.xxx.yyy  (*p1)
 * path: @root.asdf.bhd          (*p2)
 * result: ....bhd
 *
 * base: @root.asdf.bhd          (!*p1)
 * path: @root.asdf.bhd.xyz      (*p2)
 * result: xyz
 *
 *
 * base: @root.asdf.bhd.xyz      (*p1)
 * path: @root.asdf.bhd          (!*p2)
 * result: ...bhd
 *
 * base: @root.asdf.asdf         (!*p1)
 * path: @root.asdf.asdf         (!*p2)
 * result: ..asdf
 *
 * @param an absolute path and source of the result
 * @param an absolute path and destination of the result relative to <i>base</i>
 * @return a relative path to reach <i>path</i> from <i>base</i>
 *
 */
COIL_API(gchar *)
coil_path_relativize(const gchar *base,
                     const gchar *path)
{
  g_return_val_if_fail(path != NULL, NULL);
  g_return_val_if_fail(*path, NULL);

  if (base == NULL
      || *base == 0
      || COIL_PATH_IS_RELATIVE(path))
    return g_strdup(path);

  g_return_val_if_fail(!COIL_PATH_IS_ROOT(path) &&
                       !COIL_PATH_IS_ROOT(base), NULL);

  register const gchar *p1, *p2;
  const gchar          *marker = NULL;
  gchar                *dp, buffer[COIL_PATH_BUFLEN];

  p1 = base;
  p2 = path;
  dp = buffer;

  /* find the first differing character */
  while (*p1 != 0
     && *p1 == *p2)
  {
    /* keep track of the lask delim in base */
    if (G_UNLIKELY(*p1 == COIL_PATH_DELIM))
      marker = p1;

    p1++;
    p2++;
  }

  if (*p1 || !*p2)
  {
    *dp++ = COIL_PATH_DELIM; // first reference has an extra '.'

    if (marker)
    {
      register const gchar *mp = marker;
      while ((mp = strchr(mp, COIL_PATH_DELIM)))
      {
        *dp++ = COIL_PATH_DELIM;
        mp++;
      }
    }

    p2 = path + (marker - base);
  }

  dp = g_stpcpy(dp, p2 + 1);

  return g_strndup(buffer, (dp - buffer));
}

static gboolean
_path_has_container(const gchar *path,
                    const gchar *base,
                    gboolean     strict)
{
  register const gchar *p1, *p2;
  gboolean has_prefix = FALSE;

  g_return_val_if_fail(path != NULL, FALSE);
  g_return_val_if_fail(base != NULL, FALSE);

  if (COIL_PATH_IS_ROOT(base))
    return !COIL_PATH_IS_ROOT(path);

  p1 = path;
  p2 = base;

  while (*p1 != 0
    && *p1 == *p2)
  {
    p1++;
    p2++;
  }

  has_prefix = (*p1 == COIL_PATH_DELIM && *p2 == 0);

  if (strict)
    has_prefix &= (strchr(p1, COIL_PATH_DELIM) == NULL);

  return has_prefix;
}

COIL_API(gboolean)
coil_path_is_descendent(const gchar *path,
                        const gchar *maybe_container)
{
  g_return_val_if_fail(path != NULL, FALSE);
  g_return_val_if_fail(maybe_container != NULL, FALSE);

  return _path_has_container(path, maybe_container, FALSE);
}

COIL_API(gboolean)
coil_path_has_container(const gchar *path,
                        const gchar *maybe_container)
{
  g_return_val_if_fail(path != NULL, FALSE);
  g_return_val_if_fail(maybe_container != NULL, FALSE);

  return _path_has_container(path, maybe_container, TRUE);
}

