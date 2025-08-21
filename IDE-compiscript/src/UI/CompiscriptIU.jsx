import React, { useState, useRef } from 'react'
import { FaPlay } from "react-icons/fa6";
import './styles.css'

function CompiscriptIU() {

    const [code, setCode] = useState('')
    const editorRef = useRef(null)
    const highlightRef = useRef(null)

    const INDENT = '\t' // Usar tabulación para la indentación

    const replaceRange = (text, start, end, insert) => {
      return text.slice(0, start) +  insert + text.slice(end)
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

        // TAB / SHIFT+TAB
        if (e.key === 'Tab') {
          e.preventDefault()

          // Rango de líneas afectadas
          const startLine = lineStartIndex(code, start)
          const endLine = lineStartIndex(code, end)
          const endLineTerm = code.indexOf('\n', endLine)
          const selEndLineEnd = endLineTerm === -1 ? code.length : endLineTerm

          if (hasSelection) {
            const block = code.slice(startLine, selEndLineEnd)
            const lines = block.split('\n')
            let modified, deltaStart = 0, deltaEnd = 0

            if (!e.shiftKey) {
              // Indentar todas
              modified = lines.map(l => INDENT + l).join('\n')
              deltaStart = start - startLine + INDENT.length // cursor corre por indent al inicio de la primera línea si empieza dentro
              // Aumenta selección total: + indent por línea
              const linesCount = lines.length
              deltaEnd = end - start + INDENT.length * linesCount + (start - startLine >= 0 ? 0 : 0)
            } else {
              // Desindentar si empieza con INDENT
              let removedCount = 0
              modified = lines.map(l => {
                if (l.startsWith(INDENT)) {
                  removedCount++
                  return l.slice(INDENT.length)
                }
                return l
              }).join('\n')

              // Ajuste de selección
              const firstLineHadIndent = lines[0].startsWith(INDENT)
              const linesCount = lines.length
              deltaStart = start - startLine - (firstLineHadIndent ? INDENT.length : 0)
              deltaEnd = end - start - (INDENT.length * removedCount)
            }

            const newCode = replaceRange(code, startLine, selEndLineEnd, modified)
            setCode(newCode)

            // Nueva selección
            const newStart = startLine + Math.max(0, deltaStart)
            const newEnd = newStart + Math.max(0, deltaEnd)
            setSelection(newStart, Math.max(newStart, newEnd))
          } else {
            // Sin selección: insertar o quitar indent en la línea actual
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

        // ENTER: auto-indent
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

    const handleRunCode = () => {
      console.log('Ejecutando código:', code)
      // Aquí iría la lógica para ejecutar el código
    }

    const lines = code.split('\n')
    const lineNumbers = lines.map((_, index) => index + 1)

    return (
      <div className="ide-container">
        {/* Main content con sidebar y editor */}
        <div className="main-content">
          {/* Sidebar */}
          <aside className="sidebar">
            <div className="sidebar-content">
              <div className="sidebar-placeholder">
                <h3>Lineamientos del Proyecto</h3>
                <p>Contenido del sidebar...</p>
              </div>
            </div>
          </aside>
          <div className="editor-section">
            <header className="ide-header">
                <div className="ide-title">Fase de Compilación: Analizador Semántico</div>
                <button className="run-button" onClick={handleRunCode}>
                  <FaPlay />
                </button>
            </header>
            <main className="editor-container">
              <div className="editor-wrapper">
                {/* Line numbers */}
                <div className="line-numbers">
                  {lineNumbers.map((lineNum) => (
                    <div key={lineNum} className="line-number">
                      {lineNum}
                    </div>
                  ))}
                </div>
                <textarea
                  ref={editorRef}
                  className="code-editor"
                  value={code}
                  onChange={handleCodeChange}
                  onKeyDown={handleKeyDown}
                  spellCheck={false}
                />
              </div>
            </main>
          </div>
        </div>
      </div>
    )
}

export default CompiscriptIU