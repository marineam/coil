/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

G_DEFINE_TYPE(CoilNone, coil_none, G_TYPE_OBJECT);

CoilNone *coil_none_object = NULL;

static void
coil_none_class_init(CoilNoneClass *klass)
{
}

static void
coil_none_init(CoilNone *obj)
{
}

