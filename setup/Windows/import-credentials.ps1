param([string]$ContainerName = "n8n")

$files = Get-ChildItem "..\credentials\*-credentials.json"
foreach ($file in $files) {
    docker cp $file.FullName ${ContainerName}:/tmp/import-credentials.json
    docker exec $ContainerName n8n import:credentials --input /tmp/import-credentials.json
}