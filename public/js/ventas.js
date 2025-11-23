class SistemaVentas {
    constructor() {
        this.productoSeleccionado = null;
        this.initEventListeners();
    }

    getHeaders() {
        return {
            'Content-Type': 'application/json'
        };
    }

    initEventListeners() {
        // Búsqueda de productos
        $('#busqueda-producto').on('input', this.buscarProductos.bind(this));
        
        // Cantidad y preview
        $('#cantidad-producto').on('input', this.actualizarPreviewSubtotal.bind(this));
        $('#precio-manual').on('input', this.actualizarPreviewSubtotal.bind(this));
        
        // Agregar al carrito
        $('#btn-agregar-carrito').on('click', this.agregarAlCarrito.bind(this));
        
        // Finalizar venta
        $('#btn-finalizar-venta').on('click', this.finalizarVenta.bind(this));
        
        // Limpiar carrito
        $('#btn-limpiar-carrito').on('click', this.limpiarCarrito.bind(this));
        
        // Enter en búsqueda
        $('#busqueda-producto').on('keypress', (e) => {
            if (e.which === 13) {
                this.seleccionarPrimerResultado();
            }
        });
    }

    async buscarProductos(e) {
        const query = e.target.value;
        
        if (query.length < 2) {
            $('#sugerencias-productos').hide();
            return;
        }

        try {
            const response = await fetch(`/buscar-productos?q=${encodeURIComponent(query)}`, {
                headers: this.getHeaders()
            });
            const productos = await response.json();
            
            this.mostrarSugerencias(productos);
        } catch (error) {
            console.error('Error buscando productos:', error);
        }
    }

    mostrarSugerencias(productos) {
        const container = $('#sugerencias-productos');
        container.empty();
        
        if (productos.length === 0) {
            container.hide();
            return;
        }
        
        productos.forEach(producto => {
            const item = $('<button>')
                .addClass('list-group-item list-group-item-action')
                .text(producto)
                .on('click', () => this.seleccionarProducto(producto));
            container.append(item);
        });
        
        container.show();
    }

    async seleccionarProducto(nombreProducto) {
        console.log('Seleccionando producto:', nombreProducto);
        $('#busqueda-producto').val(nombreProducto);
        $('#sugerencias-productos').hide();

        try {
            const response = await fetch('/api/detalles-producto?id=' + encodeURIComponent(nombreProducto), {
                headers: this.getHeaders()
            });
            const detalles = await response.json();
            console.log('Respuesta detalles:', detalles);

            if (detalles.error) {
                this.mostrarError(detalles.error);
                return;
            }

            this.mostrarDetallesProducto(detalles);
        } catch (error) {
            console.error('Error cargando detalles:', error);
            this.mostrarError('Error al cargar detalles del producto');
        }
    }

    mostrarDetallesProducto(detalles) {
        this.productoSeleccionado = detalles;

        $('#nombre-producto').text(detalles.nombre);

        let info = [];
        if (detalles.proveedor) info.push(`🏢 ${detalles.proveedor}`);
        if (detalles.categoria) info.push(`📂 ${detalles.categoria}`);

        $('#info-producto').text(info.join(' | '));

        // Si el producto existe en BD, mostrar precio fijo
        if (detalles.existe_en_bd) {
            $('#precio-producto').html(`<strong>$${parseFloat(detalles.precio).toFixed(2)}</strong>`);
            $('#precio-manual-container').hide();
            this.productoSeleccionado.precioFijo = true;
        } else {
            // Si no existe, mostrar campo para precio manual
            $('#precio-producto').html(`<small class="text-muted">Producto no registrado</small>`);
            $('#precio-manual-container').show();
            $('#precio-manual').focus();
            this.productoSeleccionado.precioFijo = false;
        }

        $('#detalles-producto').show();
        $('#cantidad-producto').focus().select();
        this.actualizarPreviewSubtotal();
    }

    actualizarPreviewSubtotal() {
        if (!this.productoSeleccionado) return;

        const cantidad = parseInt($('#cantidad-producto').val()) || 0;
        let precio = 0;

        // Obtener precio según el tipo de producto
        if (this.productoSeleccionado.precioFijo) {
            precio = parseFloat(this.productoSeleccionado.precio);
        } else {
            precio = parseFloat($('#precio-manual').val()) || 0;
        }

        if (cantidad > 0 && precio > 0) {
            const subtotal = cantidad * precio;
            $('#preview-subtotal').text(`$${subtotal.toFixed(2)}`);
        } else {
            $('#preview-subtotal').text('$0.00');
        }
    }

    async agregarAlCarrito() {
        if (!this.productoSeleccionado) {
            this.mostrarError('Selecciona un producto primero');
            return;
        }

        const cantidad = parseInt($('#cantidad-producto').val()) || 0;

        if (cantidad <= 0) {
            this.mostrarError('La cantidad debe ser mayor a 0');
            return;
        }

        // Preparar datos para enviar
        let dataToSend = {
            producto: this.productoSeleccionado.nombre,
            cantidad: cantidad
        };

        // Si el producto no tiene precio fijo, incluir precio manual
        if (!this.productoSeleccionado.precioFijo) {
            const precioManual = parseFloat($('#precio-manual').val());
            if (!precioManual || precioManual <= 0) {
                this.mostrarError('Ingrese un precio válido para el producto');
                $('#precio-manual').focus();
                return;
            }
            dataToSend.precio = precioManual;
        }



        try {
            const response = await fetch('/agregar-carrito', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(dataToSend)
            });

            const result = await response.json();
            
            if (result.success) {
                this.mostrarCarrito(result.carrito, result.totales);
                this.limpiarBusqueda();
                this.mostrarMensaje('Producto agregado al carrito', 'success');
            } else {
                this.mostrarError(result.message);
            }
        } catch (error) {
            console.error('Error agregando al carrito:', error);
            this.mostrarError('Error al agregar producto al carrito');
        }
    }

    mostrarCarrito(carrito, totales) {
        const container = $('#carrito-items');
        const resumen = $('#resumen-carrito');
        
        if (carrito.length === 0) {
            $('#carrito-vacio').show();
            resumen.hide();
            return;
        }
        
        $('#carrito-vacio').hide();
        container.empty();
        
        carrito.forEach((item, index) => {
            const itemElement = $(`
                <div class="carrito-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1 text-warning">${item.producto}</h6>
                            <small class="text-muted">Cantidad: ${item.cantidad} × $${item.precio.toFixed(2)}</small>
                        </div>
                        <div class="text-end">
                            <div class="fw-bold text-success">$${item.subtotal.toFixed(2)}</div>
                            <button class="btn btn-sm btn-outline-danger btn-eliminar" data-index="${index}">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `);
            
            itemElement.find('.btn-eliminar').on('click', () => this.eliminarDelCarrito(index));
            container.append(itemElement);
        });
        
        // Actualizar totales
        $('#carrito-subtotal').text(`$${totales.subtotal.toFixed(2)}`);
        $('#carrito-iva').text(`$${totales.iva.toFixed(2)}`);
        $('#carrito-total').text(`$${totales.total.toFixed(2)}`);
        $('#porcentaje-iva').text(totales.porcentaje_iva);
        
        resumen.show();
    }

    async eliminarDelCarrito(index) {
        try {
            const response = await fetch(`/eliminar-carrito/${index}`, {
                method: 'DELETE',
                headers: this.getHeaders()
            });

            const result = await response.json();
            
            if (result.success) {
                this.mostrarCarrito(result.carrito, result.totales);
                this.mostrarMensaje('Producto eliminado del carrito', 'info');
            } else {
                this.mostrarError(result.message);
            }
        } catch (error) {
            console.error('Error eliminando del carrito:', error);
            this.mostrarError('Error al eliminar producto del carrito');
        }
    }

    async limpiarCarrito() {
        if (!confirm('¿Estás seguro de que quieres limpiar todo el carrito?')) {
            return;
        }

        try {
            const response = await fetch('/limpiar-carrito', {
                method: 'DELETE',
                headers: this.getHeaders()
            });

            const result = await response.json();
            
            if (result.success) {
                this.mostrarCarrito(result.carrito, result.totales);
                this.mostrarMensaje('Carrito limpiado', 'info');
            } else {
                this.mostrarError(result.message);
            }
        } catch (error) {
            console.error('Error limpiando carrito:', error);
            this.mostrarError('Error al limpiar carrito');
        }
    }

    async finalizarVenta() {
        try {
            const response = await fetch('/finalizar-venta', {
                method: 'POST',
                headers: this.getHeaders()
            });

            const result = await response.json();
            
            if (result.success) {
                this.mostrarResumenVenta(result.resumen);
                this.mostrarCarrito([], {subtotal: 0, iva: 0, total: 0, porcentaje_iva: 21});
                this.actualizarIdCliente(result.id_cliente_actual);
                this.mostrarMensaje('Venta finalizada exitosamente', 'success');
            } else {
                this.mostrarError(result.message);
            }
        } catch (error) {
            console.error('Error finalizando venta:', error);
            this.mostrarError('Error al finalizar venta');
        }
    }

    mostrarResumenVenta(resumen) {
        const contenido = `
            <div class="alert alert-success">
                <h6><i class="fas fa-check-circle me-2"></i>¡Venta Registrada Exitosamente!</h6>
            </div>
            <div class="row">
                <div class="col-6"><strong>Cliente:</strong></div>
                <div class="col-6">${resumen.id_cliente}</div>
            </div>
            <div class="row">
                <div class="col-6"><strong>Productos:</strong></div>
                <div class="col-6">${resumen.total_productos}</div>
            </div>
            <div class="row">
                <div class="col-6"><strong>Subtotal:</strong></div>
                <div class="col-6">$${resumen.totales.subtotal.toFixed(2)}</div>
            </div>
            <div class="row">
                <div class="col-6"><strong>IVA:</strong></div>
                <div class="col-6">$${resumen.totales.iva.toFixed(2)}</div>
            </div>
            <div class="row mb-3">
                <div class="col-6"><strong>Total:</strong></div>
                <div class="col-6"><strong>$${resumen.totales.total.toFixed(2)}</strong></div>
            </div>
            <div class="row">
                <div class="col-12">
                    <small class="text-muted">ID Venta: ${resumen.id_venta}</small>
                </div>
            </div>
        `;
        
        $('#resumen-venta').html(contenido);
        $('#modal-venta-exitosa').modal('show');
    }

    limpiarBusqueda() {
        $('#busqueda-producto').val('');
        $('#sugerencias-productos').hide();
        $('#detalles-producto').hide();
        $('#cantidad-producto').val('1');
        $('#precio-manual').val('');
        $('#precio-manual-container').hide();
        $('#preview-subtotal').text('$0.00');
        this.productoSeleccionado = null;
    }

    actualizarIdCliente(nuevoId) {
        $('.navbar-text').html(`<i class="fas fa-user me-1"></i>Cliente: ${nuevoId}`);
    }

    seleccionarPrimerResultado() {
        const primerResultado = $('#sugerencias-productos button:first');
        if (primerResultado.length > 0) {
            primerResultado.click();
        }
    }

    mostrarMensaje(mensaje, tipo = 'info') {
        // Implementar notificación toast
        console.log(`${tipo}: ${mensaje}`);
    }

    mostrarError(mensaje) {
        this.mostrarMensaje(mensaje, 'error');
        alert(mensaje); // Temporal - reemplazar con sistema de notificaciones
    }

    async recargarCarrito() {
        try {
            const response = await fetch('/api/obtener-carrito', {
                headers: this.getHeaders()
            });
            const result = await response.json();

            if (result.success) {
                this.mostrarCarrito(result.carrito, result.totales);
            } else {
                console.error('Error cargando carrito:', result.message);
            }
        } catch (error) {
            console.error('Error recargando carrito:', error);
        }
    }
}

// Inicializar cuando el documento esté listo
$(document).ready(function() {
    window.sistemaVentas = new SistemaVentas();
});