param([string]$ContainerName = "n8n")

$files = Get-ChildItem "..\workflow\*.json"
foreach ($file in $files) {
    docker cp $file.FullName ${ContainerName}:/tmp/import-workflow.json
    docker exec $ContainerName n8n import:workflow --input /tmp/import-workflow.json
}