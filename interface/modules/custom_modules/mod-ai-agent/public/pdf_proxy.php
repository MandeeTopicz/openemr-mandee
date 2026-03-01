<?php
/**
 * CareTopicz PDF Proxy — Fetches generated PDFs from the agent service.
 */
$file = $_GET['file'] ?? '';
if (!$file || !preg_match('#^/pdfs/[\w._-]+\.pdf$#', $file)) {
    http_response_code(400);
    echo 'Invalid file path';
    exit;
}

$agentUrl = 'http://agent:8000' . $file;
$ch = curl_init($agentUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
$pdf = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200 || !$pdf) {
    http_response_code(404);
    echo 'PDF not found';
    exit;
}

header('Content-Type: application/pdf');
header('Content-Disposition: inline; filename="' . basename($file) . '"');
header('Content-Length: ' . strlen($pdf));
echo $pdf;
