export default function handler(req, res) {
  if (req.method === 'GET') {
    res.status(200).json({ 
      message: 'API de ventas funcionando',
      ventas: []
    })
  } else {
    res.status(405).json({ error: 'Método no permitido' })
  }
}