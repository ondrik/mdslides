" Vim syntax file
" Language:     mdslides -- Markdown for LaTeX Beamer slides
" Maintainer:   see the repository this ships with
"
" Markdown with the constructs mdslides adds to it, and with the raw LaTeX
" that its passthrough rule makes ordinary rather than exceptional: maths,
" macros and environments are content here, not an escape hatch, so they are
" highlighted as such.
"
" Loaded on top of the stock markdown syntax, so lists, emphasis, code fences
" and the rest keep working and only the differences are described here.

if exists('b:current_syntax')
  finish
endif

runtime! syntax/markdown.vim
unlet! b:current_syntax

syntax case match

" ---------------------------------------------------------------------------
" Metadata: the document's block, and a slide's own
" ---------------------------------------------------------------------------

" These two come first on purpose.  Where two items match at the same place
" vim prefers the one defined last, so everything below that has to beat a
" bare '---' or a bare '\macro' -- the metadata fences, the environments --
" must be defined after them.

" A thematic break starts an untitled frame.
syn match mdslidesBreak /^\s\{0,3}\%(---\+\|\*\*\*\+\|___\+\)[ \t]*$/

syn match mdslidesLatexMacro
      \ /\\[A-Za-z@]\+\*\=\%(\[[^]\n]*\]\)\=\%({[^{}]*}\)*/
      \ contains=mdslidesMath

" The document's block is metadata only at the very start of the file and
" only when a closing fence follows; the converter applies the same rule, and
" without the fence this is an ordinary thematic break.
syn region mdslidesFrontMatter matchgroup=mdslidesMetaFence
      \ start=/\%^---[ \t]*$/ end=/^\%(---\|\.\.\.\)[ \t]*$/
      \ keepend contains=mdslidesMetaKey,mdslidesMetaComment,mdslidesMetaString

" A slide's own block: '===' opens it, '---' closes it.  The asymmetry is the
" point -- '---' alone starts a slide, and only '===' opens a block.
syn region mdslidesSlideMeta matchgroup=mdslidesMetaFence
      \ start=/^===[ \t]*$/ end=/^\%(---\|\.\.\.\)[ \t]*$/
      \ keepend contains=mdslidesSlideKey,mdslidesMetaKey,mdslidesMetaComment,
      \ mdslidesMetaString

syn match mdslidesMetaKey /^\s*[A-Za-z][-A-Za-z0-9_]*\ze\s*:/ contained
" the keys a slide understands, told apart from one it will warn about
syn match mdslidesSlideKey
      \ /^\s*\%(title\|label\|options\|itemsep\|part\|section\|subsection\)\ze\s*:/
      \ contained
syn match mdslidesMetaComment /#.*$/ contained
syn region mdslidesMetaString start=/'/ skip=/''/ end=/'/ oneline contained
syn region mdslidesMetaString start=/"/ skip=/\\"/ end=/"/ oneline contained

" ---------------------------------------------------------------------------
" Slides
" ---------------------------------------------------------------------------

" A heading, with the attribute list mdslides reads off the end of it.
syn match mdslidesHeading /^\s\{0,3}#\{1,6}\%([ \t].*\)\=$/
      \ contains=mdslidesAttributes,mdslidesMath,mdslidesMathParen,
      \ mdslidesInlineCode,mdslidesHighlight,mdslidesLatexMacro

syn match mdslidesAttributes /{[^}]*}[ \t]*$/ contained
      \ contains=mdslidesClass,mdslidesLabel,mdslidesOption
syn match mdslidesClass /\.[A-Za-z@][-A-Za-z0-9_@]*/ contained
syn match mdslidesLabel /#[A-Za-z][-A-Za-z0-9_]*/ contained
syn match mdslidesOption /[A-Za-z][-A-Za-z0-9_]*=[^ \t}]*/ contained

" ---------------------------------------------------------------------------
" Directives: '@name arguments' to '@end'
" ---------------------------------------------------------------------------

syn match mdslidesDirective /^\s\{0,3}@[A-Za-z][-A-Za-z0-9_]*/
      \ nextgroup=mdslidesDirectiveArgs
syn match mdslidesDirectiveArgs /.*$/ contained
      \ contains=mdslidesOverlay,mdslidesMath,mdslidesLatexMacro
syn match mdslidesDirectiveEnd /^\s\{0,3}@end\%([ \t]\+[A-Za-z][-A-Za-z0-9_]*\)\=[ \t]*$/
syn match mdslidesOverlay /<[^>\n]*>/ contained

" ---------------------------------------------------------------------------
" Raw LaTeX, which passthrough makes ordinary here
" ---------------------------------------------------------------------------

" An environment written out by hand is taken verbatim to its matching \end,
" so nothing inside it is Markdown.
syn region mdslidesLatexEnv matchgroup=mdslidesLatexMacro
      \ start=/^[ \t]*\\begin{\z([A-Za-z@*]\+\)}/
      \ end=/^[ \t]*\\end{\z1}/
      \ keepend contains=mdslidesMath,mdslidesMathDisplay,mdslidesLatexMacro

" \pausex is the deck's pause, and the reason a deck has a macro line at all.
syn match mdslidesPause /\\\%(pausex\|xpause\)\>/

" ---------------------------------------------------------------------------
" Maths: four spellings, none of whose contents are Markdown
" ---------------------------------------------------------------------------

syn region mdslidesMathDisplay start=/\$\$/ end=/\$\$/ keepend
      \ contains=mdslidesLatexMacro
syn region mdslidesMath start=/\$\ze[^$ \t]/ end=/\$/ oneline keepend
      \ contains=mdslidesLatexMacro
syn region mdslidesMathBracket start=/\\\[/ end=/\\\]/ keepend
      \ contains=mdslidesLatexMacro
syn region mdslidesMathParen start=/\\(/ end=/\\)/ oneline keepend
      \ contains=mdslidesLatexMacro

" ---------------------------------------------------------------------------
" Inline: the spans mdslides adds
" ---------------------------------------------------------------------------

" ==like this== becomes the highlight macro.  Three or more '=' are left
" alone, which is what keeps a setext underline safe.
syn match mdslidesHighlight /\%(=\)\@<!==[^= \t][^=]*[^= \t]==\%(=\)\@!/
syn match mdslidesHighlight /\%(=\)\@<!==[^= \t]==\%(=\)\@!/

" [text]{.macro}: the class is the macro name.
syn match mdslidesSpan /\[[^]\n]*\]{[^}\n]*}/
      \ contains=mdslidesSpanText,mdslidesClass
syn match mdslidesSpanText /\[\zs[^]\n]*\ze\]/ contained

" An image with the attribute list mdslides reads.
syn match mdslidesImage /!\[[^]\n]*\]([^)\n]*)\%({[^}\n]*}\)\=/
      \ contains=mdslidesAttributes

" ---------------------------------------------------------------------------
" Comments
" ---------------------------------------------------------------------------

" A '%' is a comment only as the first thing on its line; part-way along one
" it is passed through to LaTeX, where it comments out the rest of the line.
syn match mdslidesComment /^[ \t]*%.*$/
syn region mdslidesHtmlComment start=/<!--/ end=/-->/ keepend

" ---------------------------------------------------------------------------
" Code fences, so that a '%' or a '@' inside one is not mistaken for ours
" ---------------------------------------------------------------------------

syn region mdslidesCodeFence matchgroup=mdslidesCodeDelim
      \ start=/^\s\{0,3}\z(`\{3,}\|\~\{3,}\)\s*\%([A-Za-z0-9_+-]*\)/
      \ end=/^\s\{0,3}\z1\s*$/ keepend

" ---------------------------------------------------------------------------

hi def link mdslidesMetaFence        PreProc
hi def link mdslidesCodeFence        String
hi def link mdslidesCodeDelim        PreProc
hi def link mdslidesMetaKey          Identifier
hi def link mdslidesSlideKey         Statement
hi def link mdslidesMetaComment      Comment
hi def link mdslidesMetaString       String
hi def link mdslidesHeading          Title
hi def link mdslidesAttributes       Special
hi def link mdslidesClass            Type
hi def link mdslidesLabel            Underlined
hi def link mdslidesOption           Special
hi def link mdslidesBreak            PreProc
hi def link mdslidesDirective        Statement
hi def link mdslidesDirectiveEnd     Statement
hi def link mdslidesDirectiveArgs    Normal
hi def link mdslidesOverlay          Special
hi def link mdslidesLatexEnv         String
hi def link mdslidesLatexMacro       Function
hi def link mdslidesPause            Todo
hi def link mdslidesMath             Number
hi def link mdslidesMathDisplay      Number
hi def link mdslidesMathBracket      Number
hi def link mdslidesMathParen        Number
hi def link mdslidesHighlight        Special
hi def link mdslidesSpan             Type
hi def link mdslidesSpanText         Normal
hi def link mdslidesImage            Underlined
hi def link mdslidesComment          Comment
hi def link mdslidesHtmlComment      Comment

let b:current_syntax = 'mdslides'
