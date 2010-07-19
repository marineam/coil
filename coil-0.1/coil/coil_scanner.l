%option reentrant
%option noyywrap
%option bison-bridge
%option bison-locations

%{
/*
 * Copyright (C) 2009, 2010
 *
 * Author: John O'Connor
 */

// TODO: Add states
//
#include "coil.h"
#include "coil_parser.h"

#define YY_EXTRA_TYPE parser_context *

#define YY_USER_ACTION                                          \
  {                                                             \
    register int i = yyleng;                                    \
    yylloc->first_line = yylloc->last_line = yylineno;          \
    yylloc->filepath = yyextra->filepath;                       \
    while (i-- > 0)                                             \
      switch (yytext[i])                                        \
      {                                                         \
        case '\n':                                              \
          yylloc->last_line++;                                  \
          yylloc->last_column = 0;                              \
          break;                                                \
        case '\t':                                              \
          yylloc->last_column += 8 - (yylloc->last_column % 8); \
          break;                                                \
        default:                                                \
          yylloc->last_column++;                                \
      }                                                         \
  }


%}

D [0-9]
DOUBLE "-"?(({D}+\.{D}*)|({D}*\.{D}+))
INTEGER "-"?{D}+
COMMENT "#"[^\n]*

ROOT "@root"

KEY "-"*[a-zA-Z\_][a-zA-Z0-9_\-]*
KEY_DELIM "."

ABSOLUTE_PATH {ROOT}({KEY_DELIM}{KEY})*
RELATIVE_PATH {KEY_DELIM}*{KEY}({KEY_DELIM}{KEY})*

ESC "\\".
NEWLINE ("\r"|"\n"|"\r\n")
WHITESPACE [:space:]

DQ_CHR {ESC}|[^\\"]
SQ_CHR {ESC}|[^\\\']

MULTILINE_STRING0 [']{3}({SQ_CHR}|[']{1,2}[^'])*[']{3}
MULTILINE_STRING1 ["]{3}({DQ_CHR}|["]{1,2}[^\"])*["]{3}
MULTILINE_STRING ({MULTILINE_STRING0}|{MULTILINE_STRING1})

_STRING0 [']{SQ_CHR}*[']
_STRING1 ["]{DQ_CHR}*["]
STRING ({_STRING0}|{_STRING1})

MODULE ("@"[a-zA-Z]+)

TRUE (?i:"true")
FALSE (?i:"false")
NONE (?i:"none")

INCLUDE (?i:(("@file"|"@include")[s]?))
EXTEND (?i:"@extend"[s]?)
PACKAGE (?i:"@package")
DEBUG (?i:"@"?("debug"|"dump"))
LINK (?i:"link")

%%

{COMMENT} { ; }

{DEBUG} {
  return DEBUG_SYM;
}

{PACKAGE} {
  return PACKAGE_SYM;
}

{INCLUDE} {
  return INCLUDE_SYM;
}

{EXTEND} {
  return EXTEND_SYM;
}

{LINK}/"(" {
  return LINK_SYM;
}

{NONE} {
  new_value(yylval->value, COIL_TYPE_NONE, set_object, coil_none_object);
  return NONE_SYM;
}

{TRUE} {
  new_value(yylval->value, G_TYPE_BOOLEAN, set_boolean, TRUE);
  return TRUE_SYM;
}

{FALSE} {
  new_value(yylval->value, G_TYPE_BOOLEAN, set_boolean, FALSE);
  return FALSE_SYM;
}

{ABSOLUTE_PATH} {
  yylval->string = g_strndup(yytext, yyleng);
  return ABSOLUTE_PATH;
}

{RELATIVE_PATH} {
  yylval->string = g_strndup(yytext, yyleng);
  return RELATIVE_PATH;
}

{DOUBLE} {
  new_value(yylval->value, G_TYPE_DOUBLE,
          set_double, g_ascii_strtod(yytext, NULL));
  return DOUBLE;
}

{INTEGER} {
  new_value(yylval->value, G_TYPE_INT,
    set_int, atoi(yytext));
  return INTEGER;
}

{MULTILINE_STRING} {
  new_value(yylval->value, G_TYPE_STRING,
    take_string, g_strndup(yytext + 3, yyleng - 6));

  return STRING_LITERAL;
}

{STRING} {
  new_value(yylval->value, G_TYPE_STRING,
    take_string, g_strndup(yytext + 1, yyleng - 2));

  return STRING_LITERAL;
}

{MODULE} {
  // to be implemented later
  /* TODO: check that module exists in module table */
  if (/*XXX: found module in lookup table */FALSE)
  {
    yylval->string = g_strndup(yytext + 1, yyleng - 2);
    return MODULE_SYM;
  }
  else
    yymore();
}

"~" { return '~'; }
":" { return ':'; }
"@" { return '@'; }

"(" { return '('; }
")" { return ')'; }

"{" { return '{'; }
"}" { return '}'; }

"[" { return '['; }
"]" { return ']'; }
"," { return ','; }
"=" { return '='; }

[\n]    { yylineno++; }
[\t\r ] { ; }

. { return UNKNOWN_SYM; }

%%


