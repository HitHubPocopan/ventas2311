import { useEffect } from 'react';
import Head from 'next/head';

export default function Home() {
  useEffect(() => {
    // Load existing HTML content
    fetch('/index.html')
      .then(response => response.text())
      .then(html => {
        document.body.innerHTML = html;
        // Re-initialize JavaScript after loading HTML
        const script = document.createElement('script');
        script.src = '/js/ventas.js';
        document.body.appendChild(script);
      });
  }, []);

  return (
    <>
      <Head>
        <title>🛍️ POCOPAN - Sistema de Ventas</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" />
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />
      </Head>
      <div>Loading...</div>
    </>
  );
}