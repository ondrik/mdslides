---
title: "Symbolic Execution"
author: "Ondřej Lengál"
institute: "SAV'25, FIT VUT v Brně"
topic: "static analysis and verification"
theme: "Madrid"
colortheme: "dolphin"
fonttheme: "professionalfonts"
#mainfont: "Hack Nerd Font"
fontsize: 10pt
colorlinks: true
filecolor: blue
linkcolor: white
urlcolor: blue
linkstyle: bold
aspectratio: 169
<!--lang: en-->
titlegraphic:
logo:
date: "3 November 2025"
section-titles: false
toc: false

header-includes: |
  \usepackage{listings}
  \usepackage{tabularx}

  \input{macros.tex}
  \input{stylesheet.tex}
---

# Manual Testing
* users try **\hlbl{input vectors}**, trying to break a program
* \hlbl{pros}:
  * **complete**: a failing input vector **can be "easily" executed**
    * not always easy: concurrency, nondeterministic memory layout, etc.
  * can be directed to some *corner cases*
* \hlbl{cons}:
  * **unsound**: problematic coverage of unexpected corner cases
  * expensive (testers needed)


# Random Testing
* generate *a lot of **\hlbl{random vectors}*** and feed them into a program
* \hlbl{pros}:
  * can easily create many inputs
* \hlbl{cons}:
  * difficult to cover corner cases
  * many inputs can exercise the same paths through the program
\pausex
* e.g. QuickCheck for Haskell:

    ```Haskell
    prop_RevRev xs = reverse (reverse xs) == xs

    Main> quickCheck prop_RevRev
    OK, passed 100 tests.
    ```


# Random Testing --- Example
```C
char input[10];
read(fd, input, 10);
int counter = 0;
for (size_t i = 0; i < 10, ++i) {
  if (input[i] == 'B') {
    ++counter;
  }
}
assert(counter != 10);
```
\pausex
* difficult to hit the assertion failure:
  * there needs to be exactly 10 `B`'s read into `input`
  * all possible values of `input`: $2^{80}$
  * $P($`counter == 10`$) = 0.000000000000000000000000827$ (for uniform distribution)


# Static Analysis
**Data flow analysis**, **abstract interpretation**, \ldots:

* \hlbl{pros}:
  <!-- * can analyze all possible runs of programs 😀 -->
  * can analyze all possible runs of programs
  <!-- * sold by companies (AbsInt, Coverity, GrammaTech, etc.) 💸💸💸💸💸💸💸💸💸💸💸 -->
  * sold by companies (AbsInt, Coverity, GrammaTech, etc.)
  * easy to use (with a catch)
* \hlbl{cons}:
  * often unsound (in practice)
  * *abstraction* $\leadsto$ \hlrd{false positives} (**incomplete**)
    * it can take a lot of effort to sieve through them
  * does not provide concrete failing input vectors


# Static Analysis --- Example
```C
char input[10];
read(fd, input, 10);
int counter = 0;
for (size_t i = 0; i < 10, ++i) {
  if (input[i] == 'B') {
    ++counter;
  }
}
assert(counter != 10);
```

* e.g., abstract interpretation might just say that assert is reachable
* developer needs to assess whether it is true
* abstraction of static analysis can be different than the one used by developer


# Symbolic Execution --- A middle ground
* **Testing**: works, but each test tries only one possible execution
  * we hope that test cases generalize (no guarantees)

    \medskip
    ```C
    assert(f(2) == 21);
    assert(f(3) == 42);
    assert(f(4) == 63);
    ```
    \medskip

* **\hlbl{Symbolic Execution}**: generalizes random testing
  * allows one to assign unknown **\hlbl{symbolic}** values to variables, e.g., $\mathtt{y} = \alpha$
  * tests may then cover all possible values of the symbolic value
  
    \medskip
    ```C
    assert(f(y) == 21*(y-1));
    ```
    \medskip

  * if an execution path depends on a symbolic value, **\hlbl{fork}** execution

    \medskip
    ```C
    unsigned f(unsigned x) {
      return (x > 0)? 21*(x-1) : 13;
    }
    ```


<!-- # Spectrum of verification approaches -->
<!--  -->
<!-- **\hlrd{tady neco???????????}** -->
<!--  -->

# Symbolic Execution
* can be seen as an execution of a program in a mixed \hlbl{symbolic domain}
* similar to abstract interpretation (but with significant differences)

**Standard execution semantics**:

* in every step, all variables and allocated memory cells have concrete values
  * concrete state: configuration of a program

\pausex
**\hlbl{Symbolic} execution semantics**:

* variables and allocated memory cells can also have **\hlbl{symbolic}** values
  * e.g., $\alpha$, $2\cdot\beta + 3$, $\gamma + {}$`"Hello World"`, $\ldots$
  * symbolic values are usually introduced to represent *\hlbl{inputs}* of the program
* operators need to be extended to be able to work with symbolic values


# Symbolic Execution (cntd.)
* **\hlbl{symbolic state}** is a triple $\mathit{st} = (\mathit{line}, \mathit{store}, \mathit{pc})$ where:
  * $\mathit{line} \in \mathbb{N}$ denotes a~program line
  * $\mathit{store} : \mathit{Mem} \rightharpoonup \mathit{Sym}$ represents (symbolic) values of variables and allocated memory cells
    * $\mathit{Mem}$: the set of memory locations
    * $\mathit{Sym}$: the set of symbolic values (it also contains all concrete values)
    * ($\rightharpoonup$ denotes *partial function*)
  * $\mathit{pc}$: **\hlbl{path condition}**, a formula of first-order logic
    (over some suitable theory $\mathbb{T}$ that represents program operations and tests) that
    accumulates conditions that needed to hold to reach $\mathit{st}$
    * initially set to $\mathit{true}$
    * extended when execution is \hlbl{forked}: 
      more formulae are appended using \hlbl{conjunction} $\land$


# Extending path condition
Let $\varphi$ be a formula obtained by substituting (symbolic) values of variables into a test

* e.g. if $\mathit{store} = \{\mathtt{x} \mapsto \alpha, \mathtt{y} \mapsto 2\cdot\sin \beta, \ldots\}$, and there is a test

    ```C
    if (3 * x > log(y)) {
      stmt1;
      ...
    else {
      stmt2;
      ...
    }
    ```
  we obtain for the \texttt{if} branch
  \pausex
  $\varphi\colon 3\cdot \alpha > \log (2 \cdot \sin \beta)$


# Extending path condition (cntd.)
* $\varphi$ is a formula representing a test in a program (e.g. inside an `if` statement)
* suppose $pc$ is $\mathbb{T}$-\hlbl{satisfiable}, then at most one of the following can hold:
<!-- implications can be $\mathbb{T}$-valid: -->
  <!-- 1. $pc \to \varphi~~$ (the `then` branch) -->
  <!-- 2. $pc \to \neg \varphi$ (the `else` branch) -->
  1. $pc \Rightarrow_{\mathbb{T}} \varphi~~$ (the `then` branch)
  2. $pc \Rightarrow_{\mathbb{T}} \neg \varphi$ (the `else` branch)

  where $\Rightarrow_{\mathbb{T}}$ denotes *logical consequence* wrt.\ theory $\mathbb{T}$
  * i.e., whether all $\mathbb{T}$-models of $pc$ are also $\mathbb{T}$-models of $\varphi$ (or $\neg \varphi$)
  \pausex
* if one of the logical consequences holds, no forking and extension of $pc$ is required
  * only one branch is \hlbl{feasible}
* when neither of the consequences holds, we speak about **\hlbl{forking execution}**:
  * the execution forks because both branches are \hlbl{feasible}; $pc$ is then extended as:
    1. $pc' := pc \land \varphi~~$ (for the `then` branch) 
    2. $pc' := pc \land \neg \varphi$ (for the `else` branch)
* logical consequence is checked using an **\hlbl{SMT Solver}**


# Example of symbolic execution

:::::: columns

::: { .column width=30% }
```C
int power(x, y)
{
1:  int z = 1;
  
2:  int j = 1;
  
3:  while (y - j >= 0)
    {
4:    z *= x
    
5:    ++j;
    }
  
6:  return z
}
```
:::
<!-- column -->

::: { .column width=70% }
\newlength{\rowfill}
\setlength{\rowfill}{1mm}
\begin{tabularx}{\textwidth}{|c|c|c|c|c|X|}
  \hline
  $\mathit{line}$ & \texttt{x} & \texttt{y} & \texttt{z} & \texttt{j} & $\mathit{pc}$ \\
  \hline \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
  &&&&&\\[\rowfill]
  \hline
\end{tabularx}
:::
<!-- column -->

::::::
<!-- columns -->


# Symbolic execution --- high level algorithm {.fragile}
```lstlisting
@$symState$@ := @$(line\colon 0,~store\colon \emptyset,~pc\colon \mathit{true})$@  // initial symbolic state
@$workSet$@ := @$\{symState\}$@
while @$workSet \neq \emptyset$@:
  @$st\;$@ := @$workSet.getAndRemove$@()      // many ways to implement
  @$st'$@ := @$\textsf{symbolically execute from } st \textsf{ until a fork to } l_1 \textsf{ and } l_2 \textsf{ with condition } \varphi \textsf{, or EXIT,}$@
        @$\textsf{while checking for errors and modifying } store \textsf{ accordingly}$@
  if @$st'.line$@ == EXIT: continue
  @$workSet.add$@(@$(line\colon l_1,~store\colon st'.store,~pc\colon st'.pc \land \varphi)$@)
  @$workSet.add$@(@$(line\colon l_2,~store\colon st'.store,~pc\colon st'.pc \land \neg\varphi)$@)
```


# Symbolic execution tree
paths taken in a symbolic execution can be expressed using a **\hlbl{symbolic execution tree}**

* \hlbl{control points} of the program are nodes
* \hlbl{statements} are edges
* \hlbl{tests} that are not logical conseq.\ of the $pc$ for the branch above them have two outgoing edges:
  * $\mathit{true}$ (for `then`)
  * $\mathit{false}$ (for `else`)

**properties** of the tree:

* for every \hlbl{terminal leaf} $L$, there are concrete (non-symbolic) inputs that can navigate execution to $L$
  * a terminal leaf corresponds to a finished path
* every two terminal nodes have distinct path conditions, i.e., $pc_1 \land pc_2$ is $\mathbb{T}$-UNSAT


# Symbolic execution for verification
program verification:

* every `assume(`$\varphi$`)` (in function contracts) will update $pc' := pc \land \varphi$
* every `assert(`$\varphi$`)` will test whether $pc \Rightarrow_{\mathbb{T}} \varphi$, if
  not: \hlrd{report error}
* during execution of a program (or in preprocessing), more statements are added, e.g.:
\pausex
  * for a fixed-size array $\mathtt{a}$ of size `N`, every access `a[x]` where `x` has a symbolic value changes:

    ```C
                          assert(x < N && x >= 0);
    a[x] = y;    -->      a[x] = y;
    ```

  \pausex
  * every integer division is checked for zero-division:

    ```C
                          assert(x != 0);
    y = 42 / x;  -->      y = 42 / x;
    ```

  \pausex
  * pointer accesses are checked for `nullptr`:

    ```C
                          assert(x != nullptr);
    y = *x;      -->      y = *x;
    ```
    (checking for dereference of undefined memory locations is more difficult) 

  * etc.


# Search strategies
given by the implementation of $workSet.getAndRemove$`()`

* if **\hlbl{stack}**: DFS
  * can easily get stuck in some part of the program
\pausex
* if **\hlbl{queue}**: BFS
  * usually better, but still not guided by any higher-level knowledge
\pausex
* more complex strategies:
  * try to \hlbl{steer the search} (using priorities) towards assertion failures
  * reasoning on the *control flow graph* (CFG) of the program
\pausex
* **\hlbl{randomness}**: we don't know which paths to take$\ldots$ why not pick them randomly?
  1. pick next path uniformly at  random
  2. randomly restart search if nothing interesting found for a while
  3. when choosing between two paths with the same priority, flip a coin


# Search strategies
* **\hlbl{coverage-guided heuristics}**:
  * try to visit statements not seen before
  * increments statement's score when hit
  * pick a statement with lowest score
  * can be difficult to find how to get to a statement \pausex (undecidable)
\pausex
* **\hlbl{generational search}** (hybrid of BFS + coverage-guided):
  * **GEN 0**: pick one program path at random, run to completion
  * **GEN $n+1$**: take $pc$ from GEN $n$ and negate one branch condition, repeat
  * *modification*: negate *all* branch conditions, get several paths
  * often used with concolic execution
\pausex
* **\hlbl{combined search}**:
  * run multiple searches at once  


# Issues
* we need to test logical consequence $pc \Rightarrow_{\mathbb{T}} \varphi$ between path conditions and tests
  * reasoning in some theories is still challenging for SMT solvers
    * e.g., arithmetic over natural numbers, string variables w/ operations, \ldots
\pausex
* fixed-size/precision integer and floating-point variables in concrete execution:
  * are often represented using "\hlbl{ideal}" symbolic values from $\mathbb{N}$ or $\mathbb{R}$
  * more faithful representation uses theory of \hlbl{FixedSizeBitVectors} and \hlbl{FloatingPoint}
\pausex
* problems modelling **\hlbl{memory}**:
  * checking for invalid memory accesses `a[x]` where
    * `a` is an array and
    * `x` has a symbolic value 
  * unsatisfactory solution:
    * $\mathit{ite}(v(\mathtt{x}) = 1, v(\mathtt{a[1]}), \mathit{ite}(v(\mathtt{x}) = 2, v(\mathtt{a[2]}), \ldots))$
  * theory of arrays
  * even more problems with dynamic data structures
    * model the whole memory as a big array? $\ldots$ does not scale


# Issues
* **\hlbl{path explosion}**:
  * when symbolic execution keeps forking
  * e.g. on cycles without a fixed number of iterations
  * cf. bounded model checking (BMC)
\pausex
* **\hlbl{imprecision}**: reasons
  * pointer manipulation
  * SMT solver limitations
  * complex arithmetic operations (hashing, encryption, etc.)
  * system/library calls (e.g. $\mathtt{libc}$):
    * can contain native code
    * very complicated (e.g. call of `malloc`)
    * using a simpler version can be advantageous (e.g., $\mathtt{newlib}$, a version of $\mathtt{libc}$ for embedded systems)
    * need to make a model (a lot of work)


# Concolic testing
* **\hlbl{concolic}** = **\hlbl{conc}**rete + symb**\hlbl{olic}**
* program is executed at the same time on symbolic and concrete inputs
  * program is given *concrete inputs* $I$, which are shadowed by *symbolic values*
    * the symbolic values generalize the concrete inputs
  * execution of the program is \hlbl{instrumented}: computation of path condition
  * when a path terminates
    * choose a \hlbl{decision point} $d$ in its path condition $pc = \varphi \land d \land \psi$
    * obtain a new path condition prefix $pc' = \varphi \land \neg d$
    * generate new inputs $I' \models pc'$
    * re-run the program with $I'$ as its inputs
* for system calls, use the concrete value
  * symbolic-ness is lost at such calls
* no need to call SMT solver at conditions



# Tools
:::::: columns

::: { .column width=55% }
* **\hlbl{KLEE}**: symbolic execution of LLVM bitcode
* **\hlbl{Pex}**: symbolic execution for .NET
* **\hlbl{CREST}**: concolic testing of $\mathtt{C}$ programs
* **\hlbl{SAGE}**: targets file parsers (e.g., `.doc`, `.jpeg`)
  * used daily in Microsoft Win, Office, $\ldots$
  * found 100s of bugs in 100s of apps
:::

::: { .column width=45% }
![](klee.png "KLEE results"){ width=100% }
:::

::::::
<!-- columns -->


# Tools
* **\hlbl{Mergepoint}**: static analysis + SE
* **\hlbl{Otter}**: symbolic execution for $\mathtt{C}$
  * provide a line number
  * Otter will try to get there

* **\hlbl{Symbiotic}**: symbiosis of several approaches:
  1. program instrumentation (adding monitors for various properties)
  2. static program slicing (removing statements that are irrelevant to the property)
  3. symbolic execution based on KLEE

* **\hlbl{PyEx}**: symbolic execution of Python programs


# Used materials from
* Jan Strejček, Masaryk University
* Michael Hicks, University of Maryland
