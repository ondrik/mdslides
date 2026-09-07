\documentclass[dvipsnames,aspectratio=$aspectratio]{beamer}

\mode<presentation>
{
    \usetheme{Boadilla}
    %\usetheme{CambridgeUS}
    %\usetheme{Madrid} %%%
    %\setbeamercovered{transparent}
    %\usecolortheme{seahorse}
    \usecolortheme{dolphin}
}

\setbeamertemplate{itemize item}[square]
\setbeamertemplate{itemize subitem}[triangle]
\setbeamertemplate{itemize subsubitem}[circle]
\setbeamertemplate{enumerate item}[square]
\setbeamertemplate{section in toc}[square]
\setbeamertemplate{navigation symbols}{}

\usepackage{palatino}
\usepackage{color}
\usepackage{graphicx}

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

\title[$shorttitle]{
$title
}

\author[Havlík, \underline{\textbf{Lengál}} (Brno UT)]
{
  Jakub Havlík \and \hlbl{\bf Ondřej Lengál}
}

\institute
[]
{
Brno University of Technology, Czech Republic
}

\date[FMQC'26]{FMQC'26}

\begin{document}

% Translation of some slides only: [label=current] in the frame header.
% \includeonlyframes{current}

$slides


\backupbegin
\backupend

\end{document}
