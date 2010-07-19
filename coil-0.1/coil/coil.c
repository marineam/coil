/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

/*
 * coil_init:
 *
 * Call this before using coil. Initializes the type system
 * and the coil none type.
 */
void
coil_init(void)
{
  static gboolean init_called = FALSE;
  g_assert(init_called == FALSE);

  g_type_init();
//  g_type_init_with_debug_flags(G_TYPE_DEBUG_SIGNALS);

  coil_none_object = g_object_new(COIL_TYPE_NONE, NULL);
  init_called = TRUE;
}

/*
 * coil_location_get_type:
 *
 * Get the type identifier for #CoilLocation
 */
GType
coil_location_get_type(void)
{
  static GType type_id = 0;

  if (!type_id)
    type_id = g_pointer_type_register_static("CoilLocation");

  return type_id;
}

/*
 * coil_str_hash:
 *
 * String hash function
 */
guint
coil_str_hash(gconstpointer p)
{
  guint hash = 0;
  const guchar *key = (const guchar *)p;
  const guchar *s;

  for (s = key; *s; s++)
    hash = hash * 33 + *s;

  return hash;
}