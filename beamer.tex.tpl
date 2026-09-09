%% Beamer template for mdslides.
%%
%% The variables below are filled in from the YAML metadata block at the top
%% of the Markdown source, or from -V.  string.Template has no
%% conditionals, so build_variables() guarantees every variable below has a
%% value, falling back to a sane default when the metadata is silent.

\documentclass[$classoptions]{beamer}

\mode<presentation>
{
    % metadata: theme, colortheme, fonttheme
    % themes worth a try: Boadilla, CambridgeUS, Madrid
    % colour themes: dolphin, seahorse
    \usetheme{$theme}
    \usecolortheme{$colortheme}
    \usefonttheme{$fonttheme}
    %\setbeamercovered{transparent}
}

\setbeamertemplate{itemize item}[square]
\setbeamertemplate{itemize subitem}[triangle]
\setbeamertemplate{itemize subsubitem}[circle]
\setbeamertemplate{enumerate item}[square]
\setbeamertemplate{section in toc}[square]
\setbeamertemplate{navigation symbols}{}

\usepackage{$fontfamily}          % metadata: fontfamily
\usepackage{color}
\usepackage{graphicx}

%% Fenced code blocks become lstlisting, so the package is not optional.
%% Settings come before header-includes, so that a \lstset of your own wins.
\usepackage{listings}
%% Straight quotes in code: without this, 'B' in a listing comes out as
%% typographic quotes, which is wrong for a character literal.
\IfFileExists{upquote.sty}{\usepackage{upquote}}{}
\lstset{
  basicstyle=\ttfamily\small,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
  upquote=true,
  breaklines=true,          % long lines wrap instead of running off the slide
  breakatwhitespace=false,
}

\newcommand{\ol}[1]{\textcolor{blue}{\ifmmode \text{[OL: #1]}\else [OL: #1] \fi}}

%% Emitted at the top of every tight list, i.e. one whose items are single
%% paragraphs. \providecommand so that a header-includes of your own wins.
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

\newcommand{\hlbl}[1]{\textcolor{blue}{#1}}
\newcommand{\hlgr}[1]{\textcolor{olive!50!green}{#1}}
\newcommand{\hlrd}[1]{\textcolor{red}{#1}}
\newcommand{\hlorg}[1]{\textcolor{Orange}{#1}}
\newcommand{\hlgrey}[1]{\textcolor{black!50}{#1}}
\newcommand{\hldgr}[1]{\textcolor{olive!20!green}{#1}}




%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newcommand{\backupbegin}{
   \newcounter{finalframe}
   \setcounter{finalframe}{\value{framenumber}}
}
\newcommand{\backupend}{
   \setcounter{framenumber}{\value{finalframe}}
}

\newcommand{\xpause}[0]{\pause}
\newcommand{\pausex}[0]{\xpause}
% \newcommand{\xpause}[0]{}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% metadata: header-includes.  Last in the preamble, so that whatever it
%% pulls in (\input{macros.tex}, \input{stylesheet.tex}, ...) can override
%% what is set above.
$headerincludes

%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% The bracketed forms are the short versions beamer puts in the footline.
%% metadata: title, short-title, author, short-author, institute,
%%           short-institute, date, short-date
\title[$shorttitle]{$title}
\author[$shortauthor]{$author}
\institute[$shortinstitute]{$institute}
\date[$shortdate]{$date}

\begin{document}

% Translation of some slides only: [label=current] in the frame header.
% \includeonlyframes{current}

%% Empty when the deck has no title, or sets 'titlepage: false'.
$titlepage

$slides


\backupbegin
\backupend

\end{document}
