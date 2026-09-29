" Filetype detection for mdslides.
"
" A deck is an ordinary '.md' file, so there is no extension to go by and
" switching every Markdown file to this syntax would be presumptuous.  What
" is looked for instead is a construct that means nothing in Markdown and
" something here, which no ordinary Markdown file has by accident.
"
" To settle it by hand instead, either name the file '.mdslides', or put a
" modeline at the end of the deck:
"
"     <!-- vim: set filetype=mdslides: -->

au BufRead,BufNewFile *.mdslides setfiletype mdslides

function! s:LooksLikeADeck() abort
  " Only the head of the file, so opening a large document stays cheap.
  let fence = ''
  for l in getline(1, 80)
    " Inside a fenced block none of this means anything -- which is what
    " keeps a document *about* the format, this project's own README among
    " them, from being mistaken for a deck written in it.
    if fence !=# ''
      if l =~# '^\s\{0,3}' . fence . '\s*$'
        let fence = ''
      endif
      continue
    endif
    let m = matchstr(l, '^\s\{0,3}\zs\%(`\{3,}\|\~\{3,}\)')
    if m !=# ''
      let fence = m
      continue
    endif

    " a directive, '@theorem' or '@end', but not an e-mail address or a
    " decorator quoted mid-sentence: it has to open the line
    if l =~# '^\s\{0,3}@\%(end\>\|[A-Za-z][-A-Za-z0-9_]*\%([ \t<[{].*\)\=$\)'
      return 1
    endif
    " a slide's own metadata block
    if l =~# '^===[ \t]*$'
      return 1
    endif
    " the deck's pause
    if l =~# '\\\%(pausex\|xpause\)\>'
      return 1
    endif
  endfor
  return 0
endfunction

" 'set filetype=', not 'setfiletype': vim's own rules have already called
" the latter for '*.md', and it does nothing once a filetype is settled.
au BufRead *.md if s:LooksLikeADeck() | set filetype=mdslides | endif
