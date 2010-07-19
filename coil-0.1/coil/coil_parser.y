%{
/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */
#include "coil.h"

#define PARSE_ERROR 1
#define PARSE_OK 0

#define peek_path() (gchar *)g_queue_peek_head(YYCTX->paths)
#define pop_path() (gchar *)g_queue_pop_head(YYCTX->paths)
#define push_path(p) g_queue_push_head(YYCTX->paths, p)               \

#define peek_container()                                              \
  (CoilStruct *)g_queue_peek_head(YYCTX->containers)

#define pop_container()                                               \
  (CoilStruct *)g_queue_pop_head(YYCTX->containers)

#define push_container(c)                                             \
  g_queue_push_head(YYCTX->containers, c)

#include "coil_parser.h"

void yyerror(YYLTYPE        *yylocp,
             parser_context *ctx,
             const gchar    *msg);

static void
collect_parse_errors(GError         **error,
                     parser_context  *const ctx,
                     gboolean         number_errors)
{
  if (error == NULL)
    return; /* ignore all errors */

  g_return_if_fail(ctx != NULL);
  // should not be called unless parser reports errors
  g_return_if_fail(ctx->errors != NULL);

  guint    n;
  GList   *link;
  GString *e_msg;

  e_msg = g_string_new_len("Parse Error(s): \n",
                           sizeof("Parse Error(s): \n")-1);

  for (link = g_list_last(ctx->errors), n = 1;
       link != NULL;
       link = g_list_previous(link))
  {
    g_assert(link->data != NULL);

    GError *err = (GError *)link->data;

    if (number_errors)
    {
      g_string_append_printf(e_msg,
          "%d) %s\n", n++, (gchar*)err->message);
    }
    else
      g_string_append(e_msg, err->message);

    g_string_append_c(e_msg, '\n');
  }

  g_propagate_error(error,
    g_error_new_literal(COIL_ERROR,
                        COIL_ERROR_PARSE,
                        e_msg->str));

  g_string_free(e_msg, TRUE);
}


static gboolean
parser_check_result(parser_context *ctx)
{

  if (g_hash_table_size(ctx->prototypes))
  {
    GList *prototypes = g_hash_table_get_values(ctx->prototypes);
// XXX: this might require more than one iteration
    while (prototypes)
    {
      CoilStruct *prototype, *container;
      prototype = (CoilStruct *)prototypes->data;

      container = COIL_EXPANDABLE(prototype)->container;
      coil_struct_expand(container, &ctx->error);

      if (G_UNLIKELY(ctx->error))
      {
        ctx->errors = g_list_prepend(ctx->errors, ctx->error);
        g_list_free(prototypes);
        return FALSE;
      }

      prototypes = g_list_delete_link(prototypes, prototypes);
    }

    if (g_hash_table_size(ctx->prototypes))
    {
      GString *msg;
      GList   *path_list;

      msg = g_string_sized_new(512);

      path_list = g_hash_table_get_keys(ctx->prototypes);
      path_list = g_list_sort(path_list, (GCompareFunc)strcmp);

      while (path_list)
      {
        g_string_append_printf(msg, "%s, ", (gchar *)path_list->data);
        path_list = g_list_delete_link(path_list, path_list);
      }

      g_set_error(&ctx->error, COIL_ERROR, COIL_ERROR_PARSE,
                  "Referencing undefined struct(s). "
                  "Prototype(s) are: %s", msg->str);

      g_string_free(msg, TRUE);

      ctx->errors = g_list_prepend(ctx->errors, ctx->error);

      return FALSE;
    }
  }

  return TRUE;
}

#ifdef COIL_DEBUG
static gboolean
coil_parser_handle_debug(parser_context *const yyctx,
                         gchar          *arg)
{
  GValue *value;
  gchar  *value_str;

  if (!strcmp(arg, "clear"))
      coil_struct_clear(YYCTX->root);
  else
  {
    value = coil_struct_get_path_value(peek_container(),
                                       arg, TRUE,
                                       &YYCTX->error);
    if (G_UNLIKELY(YYCTX->error))
    {
      g_free(arg);
      return FALSE;
    }

    value_str = coil_value_to_string(value, &YYCTX->error);

    if (G_UNLIKELY(YYCTX->error))
    {
      g_free(arg);
      return FALSE;
    }

    g_print("----[Debug '%s']----\n", arg);
    g_print("%s\n", value_str);
    g_print("----[/Debug]----\n");

    g_free(value_str);
  }

  g_free(arg);
  return TRUE;
}
#else
#  define coil_parser_handle_debug(a, b) TRUE
#endif

#include "coil_scanner.h"

%}
%expect 0
%error-verbose
%defines
%locations
%require "2.0"
%pure_parser
%parse-param { parser_context *yyctx }

%token DEBUG_SYM
%token EXTEND_SYM
%token INCLUDE_SYM
%token LINK_SYM
%token MODULE_SYM
%token PACKAGE_SYM

%token ABSOLUTE_PATH
%token RELATIVE_PATH

%token TRUE_SYM
%token FALSE_SYM
%token NONE_SYM

%token DOUBLE
%token INTEGER

%token STRING_LITERAL
%token STRING_EXPRESSION

%token UNKNOWN_SYM

%left ':' ','
%right '~' '@' '='

%union {
  GValue *value;
  GList  *list;
  gchar  *string;
}

%type <string> ABSOLUTE_PATH
%type <string> RELATIVE_PATH
%type <string> path

%type <list> path_list
%type <list> path_list_items
%type <list> path_list_items_with_comma

%type <list> value_list
%type <list> value_list_items
%type <list> include_spec_args

%type <value> NONE_SYM
%type <value> TRUE_SYM
%type <value> FALSE_SYM
%type <value> DOUBLE
%type <value> INTEGER
%type <value> string
%type <value> STRING_LITERAL
%type <value> STRING_EXPRESSION
%type <value> primative
%type <value> value
%type <value> link
%type <value> link_path

%start coil

%%

coil
  : context
  {
    if (!parser_check_result(YYCTX))
      YYABORT;
  }
;

context
  : /* empty context */
  | context statement
;

statement
  : special_property
  | key_deletion
  | key_assignment
  | debug_statement
  | error
  {
    if (YYCTX->error)
    {
      YYCTX->errors = g_list_prepend(YYCTX->errors, YYCTX->error);
      YYCTX->error = NULL;
    }
    YYABORT;
  }
;

debug_statement
  : DEBUG_SYM path { if (!coil_parser_handle_debug(YYCTX, $2)) YYERROR; }
;

key_assignment
  : path ':'
  {
    gchar absolute_path[COIL_PATH_BUFLEN];
    gchar container_path[COIL_PATH_BUFLEN];

    if (COIL_PATH_IS_REFERENCE($1))
    {
      g_set_error(&YYCTX->error,
                  COIL_ERROR,
                  COIL_ERROR_PATH,
                  "The path '%s' contains invalid characters.",
                  $1);

      g_free($1);
      YYERROR;
    }

    coil_path_resolve_full(peek_path(), $1,
                          absolute_path, container_path, NULL,
                          &YYCTX->error);

    if (G_UNLIKELY(YYCTX->error))
    {
      g_free($1);
      YYERROR;
    }

    if (coil_struct_contains_path(YYCTX->root, absolute_path, FALSE))
    {
      g_set_error(&YYCTX->error,
                  COIL_ERROR,
                  COIL_ERROR_PARSE,
                  "Setting '%s' twice in '%s'.",
                  $1, peek_path());

      g_free($1);
      YYERROR;
    }

    if (!COIL_PATH_IS_ABSOLUTE($1))
    {
      g_free($1);
      push_path(g_strdup(absolute_path));
    }
    else
      push_path($1);
  }
    assignment_value
  {
    g_free(pop_path());
  }
;

assignment_value
  : value
  {
    coil_struct_set_path_value(peek_container(), peek_path(),
                              $1, &YYCTX->error);

    if (G_UNLIKELY(YYCTX->error))
    {
      free_value($1);
      YYERROR;
    }
  }
  | container
;

key_deletion
  : '~' path
  {
    coil_struct_mark_path_deleted(peek_container(), $2,
                                  NULL,
                                  &YYCTX->error);

    g_free($2);

    if (G_UNLIKELY(YYCTX->error))
      YYERROR;
  }
;

special_property
  : extend_spec
  | include_spec
;

extend_spec
  : EXTEND_SYM ':' path_list
  {
    CoilStruct *const container = peek_container();
    register const GList *link;

    for (link = $3;
         link != NULL;
         link = g_list_next(link))
    {
      coil_struct_extend_path(container,
                              (gchar *)link->data,
                              &YYCTX->error);

      if (G_UNLIKELY(YYCTX->error))
      {
        /* clean up after ourselves */
        free_string_list($3);
        YYERROR;
      }
    }

    free_string_list($3);
  }
;

include_spec
  : INCLUDE_SYM ':' include_spec_args
  {
    CoilInclude  *include;
    CoilStruct   *container = peek_container();
    const GValue *path_value;

    if ($3 == NULL
      || (path_value = (GValue *)$3->data) == NULL
      || !(G_VALUE_HOLDS(path_value, G_TYPE_STRING)
        || G_VALUE_HOLDS(path_value, COIL_TYPE_EXPANDABLE)))
    {
      g_set_error(&YYCTX->error,
                  COIL_ERROR,
                  COIL_ERROR_PARSE,
                  "Include statement must specify a filename to include as"
                  " a string or string expression.");

      free_value_list($3);
      YYERROR;
    }

    $3 = g_list_delete_link($3, $3);

    include = coil_include_new("include_path_value", path_value,
                               "import_list", $3,
                               "container", container,
                               "location", &@$);

    coil_struct_add_dependency(container, COIL_TYPE_INCLUDE, include);
  }
;

include_spec_args
  : string      { $$ = g_list_prepend(NULL, $1); }
  | link        { $$ = g_list_prepend(NULL, $1); }
  | value_list  { $$ = $1; }
;

link
  : link_path                   { $$ = $1; }
  | '=' link_path               { $$ = $2; }
;

link_path
  : path
  {
    if (G_UNLIKELY(!coil_validate_path($1)))
    {
      coil_set_error(&YYCTX->error, COIL_ERROR_PATH,
                     @$, "Invalid link path '%s'", $1);

      g_free($1);
      YYERROR;
    }

    new_value($$, COIL_TYPE_LINK, take_object,
      coil_link_new("path", $1,
                    "container", peek_container(),
                    "location", &@$));

    g_free($1);
  }
;


container
  : '{'
  {
    gchar       *path = peek_path();
    CoilStruct  *container = g_hash_table_lookup(YYCTX->prototypes, path);

    g_assert(container == NULL
            || COIL_IS_STRUCT(container));

    if (container == NULL)
    {
      GValue *value;

      /* XXX:
       * in cases where peek_path() contains more than 1 key..
       * ie. a.b.c this container will be incorrect
       * this should probably be fixed here but is replaced when set
       */
      container = coil_struct_new("container", peek_container(),
                                  "path", path,
                                  "is-prototype", FALSE,
                                  "location", &@$);

      new_value(value, COIL_TYPE_STRUCT,
                take_object, container);

      coil_struct_set_path_value(peek_container(), path,
                                  value, &YYCTX->error);

      if (G_UNLIKELY(YYCTX->error))
      {
        free_value(value);
        YYERROR;
      }
    }

    g_assert(COIL_IS_STRUCT(container));
    g_object_ref(container);
    g_object_freeze_notify(G_OBJECT(container));
    push_container(container);
  }
  context '}'
  {
    CoilStruct *container = pop_container();
    g_object_thaw_notify(G_OBJECT(container));

    if (coil_struct_is_prototype(container))
    {
      g_object_set(container,
                  "is-prototype",
                  FALSE, NULL);
    }

    g_object_unref(container);
  }
;

path_list
  : path_list_items_with_comma { $$ = g_list_reverse($1); }
  | '[' path_list_items ']'    { $$ = g_list_reverse($2); }
;

path_list_items_with_comma
  : path                                { $$ = g_list_prepend(NULL, $1); }
  | path_list_items_with_comma ',' path { $$ = g_list_prepend($1, $3); }
;

path_list_items
  : path                     { $$ = g_list_prepend(NULL, $1); }
  | path_list_items path     { $$ = g_list_prepend($1, $2); }
  | path_list_items ',' path { $$ = g_list_prepend($1, $3); }
;

value_list
  : '[' ']'                  { $$ = NULL; }
  | '[' value_list_items ']' { $$ = g_list_reverse($2); }
;

value_list_items
  : value                      { $$ = g_list_prepend(NULL, $1); }
  | value_list_items value     { $$ = g_list_prepend($1, $2); }
  | value_list_items ',' value { $$ = g_list_prepend($1, $3); }
;

value
  : primative  { $$ = $1; }
  | string     { $$ = $1; }
  | link       { $$ = $1; }
  | value_list { new_value($$, COIL_TYPE_LIST, take_boxed, $1); }
;

path
  : ABSOLUTE_PATH { $$ = $1; /*printf("ABSOLUTE_PATH ");*/}
  | RELATIVE_PATH { $$ = $1; /*printf("RELATIVE_PATH ");*/}
;

string
  : STRING_LITERAL    { $$ = $1; }
  | STRING_EXPRESSION { $$ = $1; }
;

primative
  : NONE_SYM  { $$ = $1;/*printf("NONE_SYM ");*/ }
  | TRUE_SYM  { $$ = $1;/*printf("TRUE_SYM ");*/ }
  | FALSE_SYM { $$ = $1;/*printf("FALSE_SYM ");*/ }
  | INTEGER   { $$ = $1;/*printf("INTEGER ");*/ }
  | DOUBLE    { $$ = $1;/*printf("DOUBLE ");*/ }
;

%%
extern int yydebug;

static void
parser_untrack_prototype_cb(GObject *instance,
                            GParamSpec *arg1,
                            gpointer data)
{
  g_return_if_fail(instance != NULL);
  g_return_if_fail(data != NULL);
  g_return_if_fail(COIL_IS_STRUCT(instance));

  parser_context *const ctx = (parser_context *)data;
  CoilStruct *const prototype = COIL_STRUCT(instance);

  g_return_if_fail(ctx->prototype_hook_id != 0);

  if (!coil_struct_is_prototype(prototype))
  {
//    g_debug("Removing prototype %s", coil_struct_get_path(prototype));
    g_hash_table_remove(ctx->prototypes, coil_struct_get_path(prototype));
    g_signal_handlers_disconnect_matched(instance,
                                         G_SIGNAL_MATCH_FUNC |
                                         G_SIGNAL_MATCH_DATA,
                                         0, 0, NULL,
                                         G_CALLBACK(parser_untrack_prototype_cb),
                                         data);
  }
}

static gboolean
parser_track_prototype_hook(GSignalInvocationHint *ihint,
                            guint                  n_param_values,
                            const GValue          *param_values,
                            gpointer               data)
{
  g_return_val_if_fail(data != NULL, FALSE);
  g_return_val_if_fail(n_param_values > 0, FALSE);
  g_return_val_if_fail(G_VALUE_HOLDS(&param_values[0], COIL_TYPE_STRUCT), FALSE);

  CoilStruct     *prototype;
  const gchar    *path;
  parser_context *const ctx = (parser_context *const)data;

  prototype = COIL_STRUCT(g_value_dup_object(&param_values[0]));

  if (coil_struct_get_root(prototype) != ctx->root)
    return TRUE;

  path = coil_struct_get_path(prototype);
  //g_debug("Adding prototype %s", path);
  g_hash_table_insert(ctx->prototypes, (gchar *)path, prototype);

  g_signal_connect(G_OBJECT(prototype),
                   "notify::is-prototype",
                   G_CALLBACK(parser_untrack_prototype_cb),
                   (gpointer)ctx);

  g_object_unref(prototype);

  return TRUE;
}

static void
coil_parser_ctx_init(parser_context   *const ctx,
                     void             *scanner)
{
  g_return_if_fail(ctx != NULL);
  g_return_if_fail(scanner != NULL);

  if (yylex_init_extra(ctx, &scanner))
  {
    g_error("Could not set parser context for scanner. %s",
      g_strerror(errno));
    return;
  }

  //yydebug = 1;

  ctx->prototypes     = g_hash_table_new_full(g_str_hash, g_str_equal,
                                              NULL, NULL);

  ctx->scanner      = (gpointer)scanner;
  ctx->containers   = g_queue_new();
  ctx->paths        = g_queue_new();
  ctx->error        = NULL;
  ctx->errors       = NULL;
  ctx->filepath     = NULL;
  ctx->root         = coil_struct_new();
  ctx->buffer_state = NULL;
  ctx->do_buffer_gc = FALSE;

  g_queue_push_head(ctx->containers, ctx->root);
  g_queue_push_head(ctx->paths,
                    g_strndup(COIL_ROOT_PATH, COIL_ROOT_PATH_LEN));

  ctx->prototype_hook_id =
    g_signal_add_emission_hook(g_signal_lookup("create", COIL_TYPE_STRUCT),
                               g_quark_from_static_string("prototype"),
                               (GSignalEmissionHook)parser_track_prototype_hook,
                               (gpointer)ctx, NULL);

  g_assert(ctx->prototype_hook_id);
}

static void
coil_parser_ctx_destroy(parser_context *ctx)
{
  g_return_if_fail(ctx != NULL);

  g_signal_remove_emission_hook(g_signal_lookup("create", COIL_TYPE_STRUCT),
                                ctx->prototype_hook_id);

  g_hash_table_unref(ctx->prototypes);

  while (!g_queue_is_empty(ctx->paths))
    g_free(g_queue_pop_head(ctx->paths));

  g_queue_free(ctx->paths);
  g_queue_free(ctx->containers);

  while (ctx->errors)
  {
    g_error_free(ctx->errors->data);
    ctx->errors = g_list_delete_link(ctx->errors, ctx->errors);
  }

  if (ctx->root)
    g_object_unref(ctx->root);

  if (ctx->do_buffer_gc)
    yy_delete_buffer((YY_BUFFER_STATE)ctx->buffer_state,
                      (yyscan_t)ctx->scanner);

  if (ctx->scanner)
    yylex_destroy((yyscan_t)ctx->scanner);
}

static void
coil_parser_prepare_for_stream(parser_context *const ctx,
                               FILE           *stream,
                               const gchar    *name)
{
  g_return_if_fail(ctx != NULL);
  g_return_if_fail(stream != NULL);
  g_return_if_fail(name != NULL);

  yyset_in(stream, (yyscan_t)ctx->scanner);
  ctx->filepath = name;
}

static void
coil_parser_prepare_for_string(parser_context *const ctx,
                               const char      *string,
                               gsize            len)
{
  g_return_if_fail(ctx != NULL);
  g_return_if_fail(string != NULL);
  g_return_if_fail(ctx->buffer_state == NULL);

  if (len > 0)
  {
    ctx->buffer_state = (gpointer)yy_scan_bytes(string,
                          (yy_size_t)len,
                          (yyscan_t)ctx->scanner);
  }
  else
  {
    ctx->buffer_state = (gpointer)yy_scan_string(string,
                            (yyscan_t)ctx->scanner);
  }

  if (ctx->buffer_state == NULL)
    g_error("Error preparing buffer for scanner.");

  ctx->do_buffer_gc = TRUE;
}

static void
coil_parser_prepare_for_buffer(parser_context *const ctx,
                               char           *buffer,
                               gsize           len)
{
  g_return_if_fail(ctx != NULL);
  g_return_if_fail(buffer != NULL);
  g_return_if_fail(len > 0);
  g_return_if_fail(ctx->buffer_state == NULL);

  if (buffer[len - 2]
    || buffer[len - 1])
    g_error("The last 2 bytes of buffer must be ASCII NUL.");

  ctx->buffer_state = (gpointer)yy_scan_buffer(buffer,
                        (yy_size_t)len, (yyscan_t)ctx->scanner);

  if (ctx->buffer_state == NULL)
    g_error("Error preparing buffer for scanner.");

  ctx->do_buffer_gc = TRUE;
}

COIL_API(CoilStruct *)
coil_parse_string_len(const gchar *string,
                      gsize        len,
                      GError     **error)
{
  CoilStruct    *root = NULL;
  parser_context parser;
  yyscan_t       scanner;
  gint           result;

  g_return_val_if_fail(string != NULL, NULL);

  coil_parser_ctx_init(&parser, &scanner);
  coil_parser_prepare_for_string(&parser, string, len);

  result = yyparse(&parser);

  if (result == PARSE_ERROR)
  {
    collect_parse_errors(error, &parser, TRUE);
  }
  else
  {
    g_assert(parser.errors == NULL);
    root = g_object_ref(parser.root);
  }

  coil_parser_ctx_destroy(&parser);

  return root;
}

COIL_API(CoilStruct *)
coil_parse_string(const gchar *string,
                  GError     **error)
{
  return coil_parse_string_len(string, 0, error);
}

COIL_API(CoilStruct *)
coil_parse_buffer(gchar   *buffer,
                  gsize    len,
                  GError **error)
{
  CoilStruct     *root = NULL;
  parser_context  parser;
  yyscan_t        scanner;
  gint            result;

  g_return_val_if_fail(buffer != NULL, NULL);
  g_return_val_if_fail(len > 0, NULL);

  coil_parser_ctx_init(&parser, &scanner);
  coil_parser_prepare_for_buffer(&parser, buffer, len);

  result = yyparse(&parser);

  if (result == PARSE_ERROR)
  {
    collect_parse_errors(error, &parser, TRUE);
  }
  else
  {
    g_assert(parser.errors == NULL);
    root = g_object_ref(parser.root);
  }

  coil_parser_ctx_destroy(&parser);

  return root;
}

COIL_API(CoilStruct *)
coil_parse_file(const gchar  *filepath,
                GError      **error)
{
  CoilStruct     *root = NULL;
  parser_context  parser;
  yyscan_t        scanner;
  FILE           *fp;
  gint            result;

  g_return_val_if_fail(filepath != NULL, NULL);

  if (!g_file_test(filepath,
      (G_FILE_TEST_IS_REGULAR | G_FILE_TEST_EXISTS)))
  {
    g_set_error(error, COIL_ERROR, COIL_ERROR_PARSE,
                "Unable to find file '%s'.", filepath);

    return NULL;
  }

  if (!(fp = fopen(filepath, "r")))
  {
    g_set_error(error, COIL_ERROR, COIL_ERROR_PARSE,
                "Unable to open file '%s'.", filepath);
    return NULL;
  }

  coil_parser_ctx_init(&parser, &scanner);
  coil_parser_prepare_for_stream(&parser, fp, filepath);

  result = yyparse(&parser);

  if (result == PARSE_ERROR)
  {
    collect_parse_errors(error, &parser, TRUE);
  }
  else
  {
    g_assert(parser.errors == NULL);
    root = g_object_ref(parser.root);
  }

  coil_parser_ctx_destroy(&parser);
  fclose(fp);

  return root;
}

COIL_API(CoilStruct *)
coil_parse_stream(FILE        *fp,
                  const gchar *stream_name,
                  GError     **error)
{
  CoilStruct     *root = NULL;
  parser_context  parser;
  yyscan_t        scanner;
  gint            result;

  g_return_val_if_fail(fp != NULL, NULL);

  coil_parser_ctx_init(&parser, &scanner);
  coil_parser_prepare_for_stream(&parser, fp, stream_name);

  result = yyparse(&parser);

  if (result == PARSE_ERROR)
  {
    collect_parse_errors(error, &parser, TRUE);
  }
  else
  {
    g_assert(parser.errors == NULL);
    root = g_object_ref(parser.root);
  }

  coil_parser_ctx_destroy(&parser);

  return root;
}

void yyerror(YYLTYPE        *yylocp,
             parser_context *ctx,
             const gchar    *msg)
{
  g_return_if_fail(ctx != NULL);
  g_return_if_fail(yylocp != NULL);

  ctx->errors = g_list_prepend(ctx->errors,
    coil_error_new(COIL_ERROR_PARSE,
                   (*yylocp),
                   "%s", msg));
}

