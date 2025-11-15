" Vim syntax file
" Language: CSL

if exists("b:current_syntax")
  finish
endif
let b:current_syntax = "csl"

syn keyword cslStorage const var comptime align anytype param linksection linkname export extern volatile
syn keyword cslStructure struct enum
syn keyword cslStatement asm break return continue
syn keyword cslConditional if else switch and or
syn keyword cslRepeat while for

syn keyword cslKeyword fn layout task inline noinline
syn keyword cslType bool direction cb16 bf16 f16 f32 f64 void type color input_queue output_queue
syn keyword cslType dsd comptime_int comptime_float comptime_string comptime_struct ut_id
syn keyword cslType dsr_dest dsr_src0 dsr_src1 xdsr data_task_id control_task_id local_task_id
syn keyword cslDSDKinds mem1d_dsd mem4d_dsd fabin_dsd fabout_dsd fifo_handle circbuf_dsd

syn keyword cslBoolean true false

syn match cslType "\v<[iu](8|16|32)>"

syn match cslOperator display "\V\[-+/*=^&|!><%~]"
syn match cslArrowCharacter display "\V->"

syn match cslBuiltinFn "@activate\>"
syn match cslBuiltinFn "@add16\>"
syn match cslBuiltinFn "@addc16\>"
syn match cslBuiltinFn "@allocate_fifo\>"
syn match cslBuiltinFn "@and16\>"
syn match cslBuiltinFn "@as\>"
syn match cslBuiltinFn "@assert\>"
syn match cslBuiltinFn "@bind_control_task\>"
syn match cslBuiltinFn "@bind_data_task\>"
syn match cslBuiltinFn "@bind_local_task\>"
syn match cslBuiltinFn "@bitcast\>"
syn match cslBuiltinFn "@block\>"
syn match cslBuiltinFn "@clz\>"
syn match cslBuiltinFn "@comptime_assert\>"
syn match cslBuiltinFn "@comptime_print\>"
syn match cslBuiltinFn "@concat_structs\>"
syn match cslBuiltinFn "@constants\>"
syn match cslBuiltinFn "@ctz\>"
syn match cslBuiltinFn "@dfilt\>"
syn match cslBuiltinFn "@dimensions\>"
syn match cslBuiltinFn "@element_count\>"
syn match cslBuiltinFn "@element_type\>"
syn match cslBuiltinFn "@export_name\>"
syn match cslBuiltinFn "@export_symbol\>"
syn match cslBuiltinFn "@fabsh\>"
syn match cslBuiltinFn "@fabss\>"
syn match cslBuiltinFn "@faddh\>"
syn match cslBuiltinFn "@faddhs\>"
syn match cslBuiltinFn "@fadds\>"
syn match cslBuiltinFn "@fh2s\>"
syn match cslBuiltinFn "@fh2xp16\>"
syn match cslBuiltinFn "@field\>"
syn match cslBuiltinFn "@fmach\>"
syn match cslBuiltinFn "@fmachs\>"
syn match cslBuiltinFn "@fmacs\>"
syn match cslBuiltinFn "@fmaxh\>"
syn match cslBuiltinFn "@fmaxs\>"
syn match cslBuiltinFn "@fmovh\>"
syn match cslBuiltinFn "@fmovs\>"
syn match cslBuiltinFn "@fmulh\>"
syn match cslBuiltinFn "@fmuls\>"
syn match cslBuiltinFn "@fnegh\>"
syn match cslBuiltinFn "@fnegs\>"
syn match cslBuiltinFn "@fnormh\>"
syn match cslBuiltinFn "@fnorms\>"
syn match cslBuiltinFn "@fs2h\>"
syn match cslBuiltinFn "@fs2xp16\>"
syn match cslBuiltinFn "@fscaleh\>"
syn match cslBuiltinFn "@fscales\>"
syn match cslBuiltinFn "@fsubh\>"
syn match cslBuiltinFn "@fsubs\>"
syn match cslBuiltinFn "@get_array\>"
syn match cslBuiltinFn "@get_color\>"
syn match cslBuiltinFn "@get_control_task_id\>"
syn match cslBuiltinFn "@get_data_task_id\>"
syn match cslBuiltinFn "@get_dsd\>"
syn match cslBuiltinFn "@get_filter_id\>"
syn match cslBuiltinFn "@get_int\>"
syn match cslBuiltinFn "@get_local_task_id\>"
syn match cslBuiltinFn "@get_rectangle\>"
syn match cslBuiltinFn "@get_string_from_byte\>"
syn match cslBuiltinFn "@get_symbol_id\>"
syn match cslBuiltinFn "@get_xdsr\>"
syn match cslBuiltinFn "@has_field\>"
syn match cslBuiltinFn "@import_comptime_value\>"
syn match cslBuiltinFn "@import_module\>"
syn match cslBuiltinFn "@is_comptime\>"
syn match cslBuiltinFn "@is_same_type\>"
syn match cslBuiltinFn "@is_arch\>"
syn match cslBuiltinFn "@load_to_dsr\>"
syn match cslBuiltinFn "@map\>"
syn match cslBuiltinFn "@mov16\>"
syn match cslBuiltinFn "@mov32\>"
syn match cslBuiltinFn "@or16\>"
syn match cslBuiltinFn "@popcnt\>"
syn match cslBuiltinFn "@random16\>"
syn match cslBuiltinFn "@range\>"
syn match cslBuiltinFn "@range_start\>"
syn match cslBuiltinFn "@range_step\>"
syn match cslBuiltinFn "@range_stop\>"
syn match cslBuiltinFn "@rank\>"
syn match cslBuiltinFn "@rpc\>"
syn match cslBuiltinFn "@sar16\>"
syn match cslBuiltinFn "@set_color_config\>"
syn match cslBuiltinFn "@set_config\>"
syn match cslBuiltinFn "@set_local_color_config\>"
syn match cslBuiltinFn "@set_dsd_base_addr\>"
syn match cslBuiltinFn "@increment_dsd_offset\>"
syn match cslBuiltinFn "@initialize_queue\>"
syn match cslBuiltinFn "@ptrcast\>"
syn match cslBuiltinFn "@set_dsd_length\>"
syn match cslBuiltinFn "@set_dsd_stride\>"
syn match cslBuiltinFn "@set_rectangle\>"
syn match cslBuiltinFn "@set_tile_code\>"
syn match cslBuiltinFn "@slr16\>"
syn match cslBuiltinFn "@set_active_prng\>"
syn match cslBuiltinFn "@strcat\>"
syn match cslBuiltinFn "@strlen\>"
syn match cslBuiltinFn "@sub16\>"
syn match cslBuiltinFn "@type_of\>"
syn match cslBuiltinFn "@unblock\>"
syn match cslBuiltinFn "@xor16\>"
syn match cslBuiltinFn "@xp162fh\>"
syn match cslBuiltinFn "@xp162fs\>"
syn match cslBuiltinFn "@zeros\>"
syn match cslBuiltinFn "@set_fifo_read_length\>"
syn match cslBuiltinFn "@set_fifo_write_length\>"
syn match cslBuiltinFn "@get_symbol_value\>"
syn match cslBuiltinFn "@get_dsr\>"
syn match cslBuiltinFn "@set_dsr_length\>"
syn match cslBuiltinFn "@set_dsr_base_addr\>"
syn match cslBuiltinFn "@get_config\>"
syn match cslBuiltinFn "@set_teardown_handler\>"
syn match cslBuiltinFn "@get_input_queue\>"
syn match cslBuiltinFn "@get_output_queue\>"
syn match cslBuiltinFn "@get_tensor_ptr\>"
syn match cslBuiltinFn "@has_exported_tensors\>"
syn match cslBuiltinFn "@set_control_task_table\>"
syn match cslBuiltinFn "@__internal_rpc\>"
syn match cslBuiltinFn "@get_ut_id\>"
syn match cslBuiltinFn "@set_empty_queue_handler\>"
syn match cslBuiltinFn "@queue_flush\>"

"                                     12_34  (. but not ..)? (12_34)?     (exponent  12_34)?
syn match cslDecNumber display   "\v<\d%(_?\d)*%(\.\.@!)?%(\d%(_?\d)*)?%([eE][+-]?\d%(_?\d)*)?"
syn match cslHexNumber display "\v<0x\x%(_?\x)*%(\.\.@!)?%(\x%(_?\x)*)?%([pP][+-]?\d%(_?\d)*)?"
syn match cslOctNumber display "\v<0o\o%(_?\o)*"
syn match cslBinNumber display "\v<0b[01]%(_?[01])*"

syn match cslCharacterInvalid display contained /b\?'\zs[\n\r\t']\ze'/
syn match cslCharacterInvalidUnicode display contained /b'\zs[^[:cntrl:][:graph:][:alnum:][:space:]]\ze'/
syn match cslCharacter /b'\([^\\]\|\\\(.\|x\x\{2}\)\)'/ contains=cslEscape,cslEscapeError,cslCharacterInvalid,cslCharacterInvalidUnicode
syn match cslCharacter /'\([^\\]\|\\\(.\|x\x\{2}\|u\x\{4}\|U\x\{6}\)\)'/ contains=cslEscape,cslEscapeUnicode,cslEscapeError,cslCharacterInvalid

syn region cslBlock start="{" end="}" transparent fold

syn region cslCommentLine start="//" end="$" contains=cslTodo,@Spell
syn region cslCommentLineDoc start="//[/!]/\@!" end="$" contains=cslTodo,@Spell

" TODO: match only the first '\\' within the cslMultilineString as cslMultilineStringPrefix
syn match cslMultilineStringPrefix display contained /c\?\\\\/
syn region cslMultilineString start="c\?\\\\" end="$" contains=cslMultilineStringPrefix

syn keyword cslTodo contained TODO

syn match     cslEscapeError   display contained /\\./
syn match     cslEscape        display contained /\\\([nrt\\'"]\|x\x\{2}\)/
syn match     cslEscapeUnicode display contained /\\\(u\x\{4}\|U\x\{6}\)/
syn region    cslString      start=+c\?"+ skip=+\\\\\|\\"+ end=+"+ oneline contains=cslEscape,cslEscapeUnicode,cslEscapeError,@Spell

hi def link cslDecNumber cslNumber
hi def link cslHexNumber cslNumber
hi def link cslOctNumber cslNumber
hi def link cslBinNumber cslNumber

hi def link cslBuiltinFn Function
hi def link cslKeyword Keyword
hi def link cslType Type
hi def link cslDSDKinds Type
hi def link cslCommentLine Comment
hi def link cslCommentLineDoc SpecialComment
hi def link cslTodo Todo
hi def link cslString String
hi def link cslMultilineString String
hi def link cslMultilineStringContent String
hi def link cslMultilineStringPrefix Comment
hi def link cslCharacterInvalid Error
hi def link cslCharacterInvalidUnicode cslCharacterInvalid
hi def link cslCharacter Character
hi def link cslEscape Special
hi def link cslEscapeUnicode cslEscape
hi def link cslEscapeError Error
hi def link cslBoolean Boolean
hi def link cslConstant Constant
hi def link cslNumber Number
hi def link cslArrowCharacter cslOperator
hi def link cslOperator Operator
hi def link cslStorage StorageClass
hi def link cslStructure Structure
hi def link cslStatement Statement
hi def link cslConditional Conditional
hi def link cslRepeat Repeat
