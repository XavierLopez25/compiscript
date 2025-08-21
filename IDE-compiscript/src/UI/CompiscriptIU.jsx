import React from 'react'
import { useState } from 'react'
import { MdAdd } from "react-icons/md";
import { IoMdClose } from "react-icons/io";
import { FaPlay } from "react-icons/fa6";

import './styles.css'

function CompiscriptIU() {

    const [code, setCode] = useState('')
    const [files, setFiles] = useState([
      { id: 1, name: 'main.compis', content: '', isActive: true }
    ])
    const [nextId, setNextId] = useState(2)

    const handleCodeChange = (e) => {
      const newCode = e.target.value
      setCode(newCode)
      // Actualizar el contenido del archivo activo
      setFiles(prevFiles => 
        prevFiles.map(file => 
          file.isActive ? { ...file, content: newCode } : file
        )
      )
    }

    const handleRunCode = () => {
      console.log('Ejecutando código:', code)
      // Aquí iría la lógica para ejecutar el código
    }

    const handleTabClick = (clickedFile) => {
      // Guardar contenido actual antes de cambiar
      setFiles(prevFiles => 
        prevFiles.map(file => ({
          ...file,
          isActive: file.id === clickedFile.id,
          content: file.isActive ? code : file.content
        }))
      )
      // Cargar contenido del archivo clickeado
      const activeFile = files.find(file => file.id === clickedFile.id)
      setCode(activeFile.content)
    }

    const handleAddFile = () => {
      const newFile = {
        id: nextId,
        name: `main${nextId}.compis`,
        content: '',
        isActive: false
      }
      setFiles(prev => prev.map(file => ({ ...file, isActive: false })).concat({ ...newFile, isActive: true }))
      setCode('')
      setNextId(prev => prev + 1)
    }

    const handleCloseFile = (fileToClose) => {
      if (files.length === 1) return // No cerrar si es el único archivo
      
      const newFiles = files.filter(file => file.id !== fileToClose.id)
      
      if (fileToClose.isActive && newFiles.length > 0) {
        newFiles[0].isActive = true
        setCode(newFiles[0].content)
      }
      
      setFiles(newFiles)
    }

    // Generar números de línea basados en el contenido
    const lines = code.split('\n')
    const lineNumbers = lines.map((_, index) => index + 1)

    return (
      <div className="ide-container">
        {/* Main content con sidebar y editor */}
        <div className="main-content">
          {/* Sidebar */}
          <aside className="sidebar">
            <div className="sidebar-content">
              {/* Aquí irá el contenido del sidebar más tarde */}
              <div className="sidebar-placeholder">
                <h3>Explorador</h3>
                <p>Contenido del sidebar...</p>
              </div>
            </div>
          </aside>

          {/* Editor Section con su propio header */}
          <div className="editor-section">
            {/* Header con pestañas de archivos */}
            <header className="ide-header">
              <div className="tabs-container">
                <div className="file-tabs">
                  {files.map((file) => (
                    <div 
                      key={file.id} 
                      className={`file-tab ${file.isActive ? 'active' : ''}`}
                      onClick={() => handleTabClick(file)}
                    >
                      <span className="file-name">{file.name}</span>
                      <button 
                        className="close-tab"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleCloseFile(file)
                        }}
                      >
                        <IoMdClose />
                      </button>
                    </div>
                  ))}
                  <button className="add-file-btn" onClick={handleAddFile}>
                    <MdAdd />
                  </button>
                </div>
              </div>
              
              <button className="run-button" onClick={handleRunCode}>
                <FaPlay />
              </button>
            </header>

            {/* Editor Area */}
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

                {/* Code editor */}
                <textarea
                  className="code-editor"
                  value={code}
                  onChange={handleCodeChange}
                  placeholder="Inicia a escribir tu código aquí..."
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