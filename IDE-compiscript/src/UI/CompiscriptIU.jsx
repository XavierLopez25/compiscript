import React, { useState, useRef, useMemo } from 'react'
import { FaPlay } from "react-icons/fa6";
import './styles.css'
import toast, { Toaster } from 'react-hot-toast';

const LINE_HEIGHT = 22;      
const PADDING_Y = 20;       
const PADDING_X = 20;        
const TAB_SIZE  = 2;         
const COLUMN_IS_ONE_BASED = false; 

// Expande tabs a espacios para medir visualmente como en el editor
function expandTabsToSpaces(s, tabSize) {
  let out = '';
  let col = 0;
  for (const ch of s) {
    if (ch === '\t') {
      const spaces = tabSize - (col % tabSize || 0);
      out += ' '.repeat(spaces);
      col += spaces;
    } else {
      out += ch;
      col += 1;
    }
  }
  return out;
}

function CompiscriptIU() {

  const [code, setCode] = useState('')
  const [diagnostics, setDiagnostics] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [tacCode, setTacCode] = useState([]); 

  const editorRef = useRef(null)
  const highlightRef = useRef(null)
  const lineNumbersInnerRef = useRef(null);
  const probeRef = useRef(null); // medidor oculto

  // Medición precisa en píxeles usando un espejo DOM oculto
  function measurePrefixPx(prefix) {
    const el = probeRef.current;
    if (!el) return 0;
    const expanded = expandTabsToSpaces(prefix, TAB_SIZE);
    el.textContent = expanded.length ? expanded : '';
    return el.offsetWidth || 0;
  }

  const INDENT = '\t' // Usar tabulación para la indentación

  const KEYWORDS = [
    'function', 'return', 'if', 'else', 'while', 'for', 'break', 'continue',
    'class', 'new', 'this', 'true', 'false', 'null',
    'integer', 'float', 'boolean', 'string',
  ]

  const keywordsRe = new RegExp(`\\b(${KEYWORDS.join('|')})\\b`, 'g')

  const replaceRange = (text, start, end, insert) => {
    return text.slice(0, start) + insert + text.slice(end)
  }

  const setSelection = (start, end = start) => {
    requestAnimationFrame(() => {
      if (editorRef.current) {
        editorRef.current.focus()
        editorRef.current.setSelectionRange(start, end)
      }
    })
  }

  const lineStartIndex = (text, idx) => {
    const nl = text.lastIndexOf('\n', idx - 1)
    return nl === -1 ? 0 : nl + 1
  }

  const currentLineIndent = (text, caret) => {
    const ls = lineStartIndex(text, caret)
    const lineEnd = text.indexOf('\n', ls)
    const line = text.slice(ls, lineEnd === -1 ? text.length : lineEnd)
    const m = line.match(/^(\s+)/)
    return m ? m[1] : ''
  }

  const handleCodeChange = (e) => {
    setCode(e.target.value)
  }

  const handleKeyDown = (e) => {
    const ta = editorRef.current
    if (!ta) return

    const { selectionStart: start, selectionEnd: end } = ta
    const hasSelection = start !== end

    if (e.key === 'Tab') {
      e.preventDefault()

      const startLine = lineStartIndex(code, start)
      const endLine = lineStartIndex(code, end)
      const endLineTerm = code.indexOf('\n', endLine)
      const selEndLineEnd = endLineTerm === -1 ? code.length : endLineTerm

      if (hasSelection) {
        const block = code.slice(startLine, selEndLineEnd)
        const lines = block.split('\n')
        let modified, deltaStart = 0, deltaEnd = 0

        if (!e.shiftKey) {
          modified = lines.map(l => INDENT + l).join('\n')
          deltaStart = start - startLine + INDENT.length
          const linesCount = lines.length
          deltaEnd = end - start + INDENT.length * linesCount + (start - startLine >= 0 ? 0 : 0)
        } else {
          let removedCount = 0
          modified = lines.map(l => {
            if (l.startsWith(INDENT)) {
              removedCount++
              return l.slice(INDENT.length)
            }
            return l
          }).join('\n')

          const firstLineHadIndent = lines[0].startsWith(INDENT)
          const linesCount = lines.length
          deltaStart = start - startLine - (firstLineHadIndent ? INDENT.length : 0)
          deltaEnd = end - start - (INDENT.length * removedCount)
        }

        const newCode = replaceRange(code, startLine, selEndLineEnd, modified)
        setCode(newCode)

        const newStart = startLine + Math.max(0, deltaStart)
        const newEnd = newStart + Math.max(0, deltaEnd)
        setSelection(newStart, Math.max(newStart, newEnd))

      } else {
        if (!e.shiftKey) {
          const newCode = replaceRange(code, start, end, INDENT)
          setCode(newCode)
          setSelection(start + INDENT.length)
        } else {
          const ls = lineStartIndex(code, start)
          if (code.slice(ls, ls + INDENT.length) === INDENT) {
            const newCode = replaceRange(code, ls, ls + INDENT.length, '')
            const shift = start - INDENT.length >= ls ? INDENT.length : 0
            setCode(newCode)
            setSelection(start - shift)
          }
        }
      }
      return
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      const indent = currentLineIndent(code, start)
      const insert = '\n' + indent
      const newCode = replaceRange(code, start, end, insert)
      setCode(newCode)
      setSelection(start + insert.length)
      return
    }
  }

  // Sentinelas únicos (no aparecen en el texto normal)
  const S = {
    KW_OPEN: '\uE000', KW_CLOSE: '\uE001',
    NUM_OPEN: '\uE002', NUM_CLOSE: '\uE003',
    STR_OPEN: '\uE004', STR_CLOSE: '\uE005',
    CMT_OPEN: '\uE006', CMT_CLOSE: '\uE007',
    OP_OPEN: '\uE008', OP_CLOSE: '\uE009',
    BR_OPEN: '\uE00A', BR_CLOSE: '\uE00B',
  }

  const markTokens = (raw) => {
    let t = raw

    // comentarios de bloque
    t = t.replace(/\/\*[\s\S]*?\*\//g, m => `${S.CMT_OPEN}${m}${S.CMT_CLOSE}`)
    // comentarios de línea
    t = t.replace(/\/\/.*/g, m => `${S.CMT_OPEN}${m}${S.CMT_CLOSE}`)
    // strings "..."
    t = t.replace(/"(?:\\.|[^"\\])*"/g, m => `${S.STR_OPEN}${m}${S.STR_CLOSE}`)
    // strings '...'
    t = t.replace(/'(?:\\.|[^'\\])*'/g, m => `${S.STR_OPEN}${m}${S.STR_CLOSE}`)
    // números
    t = t.replace(/\b\d+(?:\.\d+)?\b/g, m => `${S.NUM_OPEN}${m}${S.NUM_CLOSE}`)
    // palabras clave
    t = t.replace(keywordsRe, m => `${S.KW_OPEN}${m}${S.KW_CLOSE}`)
    // llaves/paréntesis/corchetes
    t = t.replace(/[\{\}\[\]\(\)]/g, m => `${S.BR_OPEN}${m}${S.BR_CLOSE}`)
    // operadores comunes
    t = t.replace(/(\+|\-|\*|\/|==|!=|<=|>=|<|>|\|\||&&|!|=|:|;|,)/g,
      m => `${S.OP_OPEN}${m}${S.OP_CLOSE}`)

    return t
  }

  // Escapa HTML
  const escapeHtml = (s) =>
    s.replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')

  // Convierte sentinelas a spans + maquilla saltos/espacios
  const finalizeHtml = (escaped) => {
    return escaped
      .replace(new RegExp(S.KW_OPEN, 'g'), '<span class="tok-kw">')
      .replace(new RegExp(S.KW_CLOSE, 'g'), '</span>')
      .replace(new RegExp(S.NUM_OPEN, 'g'), '<span class="tok-number">')
      .replace(new RegExp(S.NUM_CLOSE, 'g'), '</span>')
      .replace(new RegExp(S.STR_OPEN, 'g'), '<span class="tok-string">')
      .replace(new RegExp(S.STR_CLOSE, 'g'), '</span>')
      .replace(new RegExp(S.CMT_OPEN, 'g'), '<span class="tok-comment">')
      .replace(new RegExp(S.CMT_CLOSE, 'g'), '</span>')
      .replace(new RegExp(S.OP_OPEN, 'g'), '<span class="tok-op">')
      .replace(new RegExp(S.OP_CLOSE, 'g'), '</span>')
      .replace(new RegExp(S.BR_OPEN, 'g'), '<span class="tok-brace">')
      .replace(new RegExp(S.BR_CLOSE, 'g'), '</span>')
  }

  const highlightCode = (raw) => {
    if (!raw) return '&nbsp;'

    const marked = markTokens(raw)
    const escaped = escapeHtml(marked)
    const finalized = finalizeHtml(escaped)

    return finalized
      .replace(/\n/g, '\n')
      .replace(/\t/g, '\t')
  }

  const highlighted = useMemo(() => highlightCode(code), [code])

  const syncScroll = () => {
    if (!editorRef.current || !highlightRef.current) return;
    const top = editorRef.current.scrollTop;
    const left = editorRef.current.scrollLeft;

    highlightRef.current.scrollTop = top;
    highlightRef.current.scrollLeft = left;

    if (lineNumbersInnerRef.current) {
      lineNumbersInnerRef.current.style.transform = `translateY(${-top}px)`;
    }
  };

  async function analyzeCode(code, { returnAsDot = false, generateTac = true } = {}) {
    const res = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        return_ast_dot: returnAsDot,
        generate_tac: generateTac
      }),
    });
    return res.json();
  }

  const handleRunCode = async () => {
    try {
      setIsRunning(true);
      const result = await analyzeCode(code, { returnAsDot: false, generateTac: true });
      setDiagnostics(result.diagnostics || []);

      if (result.ok) {
        if (result.tac) {
          setTacCode(result.tac.code);
          console.log("Código TAC generado:", result.tac);
          toast.success('¡Compilación exitosa! Código TAC generado.', {
            duration: 3000,
            position: 'top-right',
          });
        } 
      } else {
        setTacCode([]);
        toast.error('Hubo problemas en la compilación', {
          duration: 3000,
          position: 'top-right',
        });
      }

    } catch (e) {
      setDiagnostics([{
        kind: "client",
        message: "No se pudo conectar con el analizador.",
      }]);
      setTacCode([]);
      toast.error('No se pudo conectar con el analizador', {
        duration: 3000,
        position: 'top-right',
      });
    } finally {
      setIsRunning(false);
    }
  };

  const lines = code.split('\n')
  const lineNumbers = lines.map((_, index) => index + 1)

  // Marcadores de error medidos en píxeles reales
  const markers = useMemo(() => {
    const ls = code.split('\n');

    return (diagnostics || []).map((d, i) => {
      const lineIdx = Math.max(0, (d.line ?? 1) - 1);
      const rawLine = ls[lineIdx] ?? '';

      const col0 = Math.max(0, (d.column ?? 0) - (COLUMN_IS_ONE_BASED ? 1 : 0));
      const len = Math.max(1, d.length ?? 1);

      const prefix   = rawLine.slice(0, col0);
      const untilEnd = rawLine.slice(0, col0 + len);

      const pxStart = measurePrefixPx(prefix);
      const pxEnd   = measurePrefixPx(untilEnd);
      const width   = Math.max(2, pxEnd - pxStart);

      const top  = PADDING_Y + lineIdx * LINE_HEIGHT;
      const left = PADDING_X + pxStart;

      return { i, top, left, width, message: d.message || '' };
    });
  }, [diagnostics, code]);

  return (
    <div className="ide-container">
      <Toaster />
      <div className="main-content">
        <aside className="sidebar">
          <div className="sidebar-content">
            <div className="sidebar-placeholder">
              <h3>Código TAC generado</h3>
              {tacCode.length > 0 ? (
                <pre style={{ 
                  fontFamily: 'monospace', 
                  fontSize: '15px', 
                  lineHeight: '1.5',
                  whiteSpace: 'pre',
                  overflow: 'auto'
                }}>
                  {tacCode.filter(line => !line.trim().startsWith('#')).join('\n')}
                </pre>
              ) : (
                <p>Ejecuta el código para ver el TAC generado...</p>
              )}
            </div>
          </div>
        </aside>

        <div className="editor-section">
          <header className="ide-header">
            <div className="ide-title">Fase de Compilación: Analizador Semántico</div>
            <button className="run-button" onClick={handleRunCode} disabled={isRunning}>
              <FaPlay />
            </button>
          </header>

          <main className="editor-container">
            <div className="editor-wrapper">
              <div className="line-numbers">
                <div className="line-numbers-inner" ref={lineNumbersInnerRef}>
                  {lineNumbers.map((n) => {
                    const error = diagnostics.find(d => d.line === n);
                    return (
                      <div
                        key={n}
                        className={`line-number ${error ? 'line-error' : ''}`}
                        title={error ? error.message : ''}
                      >
                        {n}
                      </div>
                    );
                  })}
                </div>
              </div>

              <pre ref={highlightRef} className="code-highlights" aria-hidden="true">
                <code
                  dangerouslySetInnerHTML={{ __html: highlighted || '&nbsp;' }}
                />
                {markers.map(m => (
                  <div
                    key={m.i}
                    className="error-marker"
                    style={{ top: `${m.top}px`, left: `${m.left}px`, width: `${m.width}px` }}
                    title={m.message}
                  />
                ))}
              </pre>

              <textarea
                ref={editorRef}
                className="code-editor"
                value={code}
                onChange={handleCodeChange}
                onScroll={syncScroll}
                onKeyDown={handleKeyDown}
                spellCheck={false}
                autoComplete="off"
                autoCapitalize="off"
                autoCorrect="off"
                wrap="off"
              />

              {/* Probe oculto para medición 1:1 con el render */}
              <div ref={probeRef} className="measure-probe"></div>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

export default CompiscriptIU
