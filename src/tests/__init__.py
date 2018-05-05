from strip_hints import strip_on_import
code_string = strip_on_import(__file__, to_empty=False, no_ast=False,
                              no_colon_move=False, only_assigns_and_defs=False,
                              py3_also=False)
