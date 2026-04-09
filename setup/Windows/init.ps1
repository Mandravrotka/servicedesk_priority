param([string]$ContainerName = "n8n")

docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при запуске контейнеров"
    exit 1
}

Write-Host "Ожидание готовности контейнеров (15 сек)..."
Start-Sleep -Seconds 15

Write-Host "Загрузка модели эмбеддингов mxbai-embed-large..."
docker exec ollama ollama pull mxbai-embed-large
if ($LASTEXITCODE -ne 0) {
    Write-Host "Предупреждение: Не удалось загрузить модель mxbai-embed-large"
    Write-Host "Выполните вручную: docker exec ollama ollama pull mxbai-embed-large"
}

.\import-credentials.ps1 -ContainerName $ContainerName
.\import-workflow.ps1 -ContainerName $ContainerName
