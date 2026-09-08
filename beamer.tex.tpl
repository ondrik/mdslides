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
\lstset{
  basicstyle=\ttfamily\small,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
}

\newcommand{\ol}[1]{\textcolor{blue}{\ifmmode \text{[OL: #1]}\else [OL: #1] \fi}}

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

$slides


\backupbegin
\backupend

\end{document}
