/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#ifndef _COIL_VALUE_H
#define _COIL_VALUE_H

#define new_value(dst, type, v_func, ptr)                         \
        G_STMT_START                                              \
        {                                                         \
          dst = g_slice_new0(GValue);                             \
          g_value_init(dst, type);                                \
          G_PASTE_ARGS(g_value_,v_func)(dst, ptr);                \
        }                                                         \
        G_STMT_END

G_BEGIN_DECLS

GValue *
copy_value(const GValue *value);

void
free_value(gpointer value);

void
free_value_list(GList *list);

void
free_string_list(GList *list);

void
coil_value_build_string(const GValue  *value,
                        GString       *const buffer,
                        GError       **error);

gchar *
coil_value_to_string(const GValue *value,
                     GError **error);

gint
coil_value_compare(const GValue *,
                   const GValue *,
                   GError      **) G_GNUC_CONST;

G_END_DECLS

#endif
