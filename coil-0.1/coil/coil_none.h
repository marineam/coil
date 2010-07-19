/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef _COIL_NONE_H
#define _COIL_NONE_H

typedef struct _CoilNone      CoilNone;
typedef struct _CoilNoneClass CoilNoneClass;

#define COIL_TYPE_NONE (coil_none_get_type())
extern CoilNone *coil_none_object;

struct _CoilNone
{
  GObject parent_instance;
};

struct _CoilNoneClass
{
  GObjectClass parent_class;
};

G_BEGIN_DECLS

GType
coil_none_get_type(void) G_GNUC_CONST;

G_END_DECLS

#endif
