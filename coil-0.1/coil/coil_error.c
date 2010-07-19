/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

/*
 * coil_error_quark:
 *
 * Return error identifier for Glib Error Handling
 */
GQuark coil_error_quark(void)
{
  return g_quark_from_static_string("coil-error-quark");
}

