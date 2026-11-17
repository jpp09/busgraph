$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path 'artifacts/Teoria_dos_Grafos_no_BusGraph.docx').Path
$outputDir = (Resolve-Path 'artifacts').Path + '\rendered-word'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$pdfPath = Join-Path $outputDir 'Teoria_dos_Grafos_no_BusGraph.pdf'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($inputPath, $false, $true)
    $document.SaveAs2($pdfPath, 17)
    $document.Close($false)
} finally {
    $word.Quit()
}
Write-Output $pdfPath
