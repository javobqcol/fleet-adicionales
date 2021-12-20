# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
import logging

_logger = logging.getLogger(__name__)


class VehicleWork(models.Model):
    _name = 'fleet.vehicle.work'
    _description = 'Fecha inicial, fecha final, estado del trabajo'
    _order = 'name_seq desc'

    name_seq = fields.Char(
        string='Consecutivo',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañia',
        default=lambda self: self.env.company,
        ondelete='restrict'
    )
    contractor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contratista',
        requiered=True,
        ondelete='restrict'
    )
    fecha_inicio = fields.Date(
        string='Fecha inicial',
        default=fields.Date.today
    )
    fecha_final = fields.Date(
        string='Fecha final'
    )
    contacto_id = fields.Many2one(
        comodel_name='res.partner',
        string='Responsable'
    )
    active = fields.Boolean(
        string="Trabajo activo?",
        default=True
    )
    state = fields.Selection(
        selection=[('activo', 'Activo'), ('inactivo', 'Inactivo'), ('cancelado', 'Cancelado'),
                   ('finalizado', 'Finalizado')],
        string='Estado del trabajo',
        default='activo',
        help='Estado del trabajo',
        required=True
    )
    descripcion = fields.Text(
        string="Descripcion del trabajo",
        placeholder="Espacio para describir detalles propios del trabajo"
    )
    detalle_ids = fields.One2many(
        comodel_name='fleet.vehicle.work.det',
        inverse_name='work_id'
    )
    alias_work = fields.Char(
        string="Nombre del trabajo",
        help="Digite el nombre con el que se conoce el trabajo"
    )
    liquidacion_ids = fields.One2many(
        comodel_name='fleet.vehicle.work.liq',
        inverse_name='work_id'
    )
    viajes_count = fields.Integer(
        compute="_compute_count_all",
        string="Historia de viajes realizados"
    )
    odometer_count = fields.Integer(
        compute="_compute_count_all",
        string='Odometer'
    )

    def _compute_count_all(self):
        LogViajes = self.env['fleet.vehicle.viaje']
        Odometer = self.env['fleet.vehicle.odometer']
        for record in self:
            record.odometer_count = Odometer.search_count(
                [('work_id', '=', record.id)]
            )
            record.viajes_count = sum(
                LogViajes.search([('work_id', '=', record.id)]).mapped(
                    'viajes'
                )
            )

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code(
                'fleet-adicionales.fleet.vehicle.work.sequence'
            ) or _(
                'New'
            )
        result = super().create(vals)
        return (result)

    def name_get(self):
        res = []
        for field in self:
            res.append(
                (field.id, '%s (%s) / %s' % (field.name_seq,
                                             field.contractor_id.name,
                                             field.alias_work or "")))
        return res

    def return_action_to_open_viajes(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet-adicionales', xml_id)
            res.update(
                context=dict(self.env.context, default_work_id=self.id, group_by=False),
                domain=[('work_id', '=', self.id)]
            )
            return res
        return False

    def return_action_to_open_odometer(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            res.update(
                context=dict(self.env.context, default_work_id=self.id, group_by=False),
                domain=[('work_id', '=', self.id)]
            )
            return res
        return False

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', '|', ('name_seq', operator, name), ('contractor_id.name', operator, name),
                         ('alias_work', operator, name)]
        model_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(model_ids).with_user(name_get_uid))

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        country = self.env.ref('base.co', raise_if_not_found=False)
        res.update({
            'fecha_inicio': fields.Date.context_today(self)
        })
        return res


class VehicleWorkDet(models.Model):
    _name = 'fleet.vehicle.work.det'
    _description = 'Vehículos/Maquinaria destinada a un trabajo'

    work_id = fields.Many2one(
        comodel_name='fleet.vehicle.work',
        string='Trabajo'
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='vehículo a Asignar'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañia',
        default=lambda self: self.env.company,
        ondelete='restrict'
    )
    standby = fields.Boolean(
        string="Standby?",
        default=False
    )
    unidades_standby = fields.Float(
        string="Unidades minimas",
        help="Unidades de standby"
    )
    precio_unidad = fields.Float(
        string='Valor de la Hora'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id'
    )
    inactivo = fields.Boolean(
        string='Inactivo',
        default=False
    )


class VehicleWorkLiquidacion(models.Model):
    _name = 'fleet.vehicle.work.liq'
    _description = 'liquidacion de trabajo segun fecha trabajo'
    _order = 'name_seq desc'

    work_id = fields.Many2one(
        comodel_name='fleet.vehicle.work',
        ondelete='restrict',
        string='Trabajo'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañia',
        default=lambda self: self.env.company,
        ondelete='restrict'
    )
    name_seq = fields.Char(
        string='Liquidacion',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    date = fields.Date(
        string='Fecha inicio',
        help="Fecha inicio liquidacion en blanco para inicio de los tiempos"
    )
    date_end = fields.Date(
        string='Fecha fin',
        help="Fecha inicio liquidacion en blanco para fin de los tiempos",
        default=fields.Date.today
    )
    total_liquidacion = fields.Float(
        string="Total liquidacion"
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id'
    )
    descripcion = fields.Text(
        string="Descripcion del liquidacion",
        placeholder="Espacio para describir cualquier aspecto"
    )
    viaje_ids = fields.One2many(
        comodel_name='fleet.vehicle.viaje',
        inverse_name='liq_id',
        string='Vehiculo'
    )
    odometer_ids = fields.One2many(
        comodel_name='fleet.vehicle.odometer',
        inverse_name='liq_id',
        string='maquinaria'
    )
    liquidado = fields.Boolean(
        String="Liquidado",
        default=False
    )
    vehicle_liq_det_ids = fields.One2many(
        comodel_name='fleet.vehicle.work.liq.det',
        inverse_name='vehicle_liq_id',
        string='Vehiculos'
    )

    def name_get(self):
        res = []
        for field in self:
            res.append(
                (
                    field.id, '%s - %s' % (
                        field.name_seq or "",
                        field.work_id.display_name or ""
                    )
                )
            )
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', ('name_seq', operator, name), ('work_id', operator, name)]
        model_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(model_ids).with_user(name_get_uid))

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code(
                'fleet-adicionales.fleet.vehicle.work.liq.sequence'
            ) or _(
                'New'
            )
        result = super().create(vals)
        return result

    def liquidar_maquinaria(self):
        for reg in self:
            for registro_liq_det in reg.vehicle_liq_det_ids:
                inicio = registro_liq_det.date
                fin = registro_liq_det.date_end
                if reg.work_id:
                    lista = [('work_id', '=', reg.work_id.id),
                             ('liq_id', '=', False),
                             ('vehicle_id', '=', registro_liq_det.vehicle_id.id)]
                    if inicio:
                        lista.append(
                            (
                                'date', '>=', inicio
                            )
                        )
                    if fin:
                        lista.append(
                            (
                                'date', '<=', fin
                            )
                        )
                    registros = registro_liq_det.env['fleet.vehicle.viaje'].search(lista)
                    inc = 1
                    if registros:
                        for record in registros:
                            record.write({'liq_id': reg.id})
                            _logger.info(
                                'FYI: -->record = %s, vehiculo = %s, interno=%s, cantera=%s' %
                                (inc, registro_liq_det.vehicle_id.name, record.recibo_interno, record.recibo_cantera)
                            )
                            inc += 1
                    registros = registro_liq_det.env['fleet.vehicle.odometer'].search(lista)
                    inc = 1
                    if registros:
                        for record in registros:
                            _logger.info(
                                'FYI: -->record = %s, vehiculo = %s, recibo=%s' %
                                (inc, registro_liq_det.vehicle_id.name, record.recibo)
                            )
                            inc += 1
                            record.write({'liq_id': reg.id})
            if reg.vehicle_liq_det_ids:
                reg.liquidado = True

    def rollback_maquinaria(self):

        for reg in self:
            _logger.info('FYI: This is odometer %s' % reg.name_seq)
            registros_viaje = reg.env['fleet.vehicle.viaje'].search([('liq_id', '=', reg.id)])
            # _logger.info('FYI: This is viajes %s' % registros_viaje)
            inc = 1
            if registros_viaje:
                for record in registros_viaje:
                    _logger.info(
                        'FYI: -->record = %s, vehiculo = %s, interno=%s, cantera=%s' %
                        (inc, record.vehicle_id.name, record.recibo_interno, record.recibo_cantera)
                    )
                    inc += 1
                    record.update(
                        {'liq_id': False}
                    )
            registros_odometer = reg.env['fleet.vehicle.odometer'].search([('liq_id', '=', reg.id)])
            inc = 1
            if registros_odometer:
                _logger.info('FYI: This is odometer %s' % registros_odometer)
                for record in registros_odometer:
                    _logger.info(
                        'FYI: -->record = %s, vehiculo = %s, interno=%s' %
                        (inc, record.vehicle_id.name, record.recibo)
                    )
                    inc += 1
                    record.update(
                        {'liq_id': False}
                    )

            reg.liquidado = False

    @api.onchange('work_id')
    def cambio_work(self):
        for reg in self:
            if reg.work_id:
                odometro = self.env['fleet.vehicle.odometer'].search(
                    [('work_id', '=', reg.work_id.id), ('liq_id', '=', False), ('tipo_odometro', '=', 'odometer')],
                    order="vehicle_id desc"
                )
                lista = [(5, 0, 0)]
                vehiculo = False
                for record in odometro:
                    if record.vehicle_id.id != vehiculo:
                        lista.append(
                            (
                                0, 0, {
                                    'vehicle_id': record.vehicle_id.id,
                                    'date_end': reg.date_end,
                                    'date': reg.date,
                                }
                            )
                        )
                    vehiculo = record.vehicle_id.id
                viajes = reg.env['fleet.vehicle.viaje'].search(
                    [('work_id', '=', reg.work_id.id), ('liq_id', '=', False)],
                    order="vehicle_id desc"
                )
                vehiculo = False
                for record in viajes:
                    if record.vehicle_id.id != vehiculo:
                        lista.append(
                            (
                                0, 0, {
                                    'vehicle_id': record.vehicle_id.id,
                                    'date_end': reg.date_end,
                                    'date': reg.date,
                                }
                            )
                        )
                        vehiculo = record.vehicle_id.id
                if lista:
                    reg.update(
                        {
                            'vehicle_liq_det_ids': lista,
                        }
                    )


class VehicleWorkLiquidacionDetalle(models.Model):
    _name = 'fleet.vehicle.work.liq.det'
    _description = 'liquidacion de maquinas y automotores detalle'

    vehicle_liq_id = fields.Many2one(
        comodel_name='fleet.vehicle.work.liq',
        ondelete='restrict'
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehiculo/maquinaria',
        help='Vehiculo/maquinaria'
    )
    date = fields.Date(
        string='Fecha inicio',
        help="Fecha inicio liquidacion en blanco para inicio de los tiempos"
    )
    date_end = fields.Date(
        string='Fecha fin',
        help="Fecha inicio liquidacion en blanco para fin de los tiempos"
    )
    total_liquidacion = fields.Float(
        string="Total liquidacion"
    )
    nota = fields.Char(
        string="Nota liquidacion vehiculo"
    )


class EmployeWorkLiquidacion(models.Model):
    _name = 'fleet.vehicle.driver.liq'
    _description = 'liquidacion de maquinas y viajes de Conductores'
    _order = 'name_seq desc'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañia',
        default=lambda self: self.env.company,
        ondelete='restrict'
    )
    name_seq = fields.Char(
        string='Secuencia',
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    note = fields.Char(
        string="Nota de liquidacion"
    )
    driver_id = fields.Many2one(
        comodel_name='res.partner',
        string='Conductor',
        help='Conductor/operador'
    )
    date = fields.Date(
        string='Fecha inicio',
        help="Fecha inicio liquidacion en blanco para inicio de los tiempos"
    )
    date_end = fields.Date(
        string='Fecha fin',
        help="Fecha inicio liquidacion en blanco para fin de los tiempos",
        default=fields.Date.today
    )
    total_liquidacion = fields.Float(
        string="Total liquidacion"
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id'
    )
    descripcion = fields.Text(
        string="Descripcion del liquidacion",
        placeholder="Espacio para describir cualquier aspecto"
    )
    driven_liq_det_ids = fields.One2many(
        comodel_name='fleet.vehicle.driver.liq.det',
        inverse_name='driver_liq_id',
        string='Detalle'
    )
    viaje_ids = fields.One2many(
        comodel_name='fleet.vehicle.viaje',
        inverse_name='liq_driver_id',
        string='Vehiculo'
    )
    odometer_ids = fields.One2many(
        comodel_name='fleet.vehicle.odometer',
        inverse_name='liq_driver_id',
        string='Maquinaria'
    )
    liquidado = fields.Boolean(
        String="Liquidado",
        default=False
    )

    def name_get(self):
        res = []
        for field in self:
            res.append(
                (
                    field.id,
                    '%s - %s' % (
                        field.name_seq or "",
                        field.note or ""
                    )
                )
            )
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', ('name_seq', operator, name), ('driver_id', operator, name)]
        model_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(model_ids).with_user(name_get_uid))

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('fleet-adicionales.fleet.vehicle.driver.sequence') \
                               or _('New')
        _logger.info('FYI: por aqu pase %s' % vals)
        result = super().create(vals)
        return (result)

    @api.onchange('date', 'date_end')
    def cambio_fecha_fin(self):
        for reg in self:
            odometro = reg.env['fleet.vehicle.odometer'].search(
                [('liq_driver_id', '=', False), ('driver_id', '!=', False), ('tipo_odometro', '=', 'odometer')],
                order="driver_id desc"
            )
            conductor = False
            lista = [(5, 0, 0)]
            for record in odometro:
                if record.driver_id.id != conductor:
                    lista.append(
                        (
                            0, 0, {
                                'driver_id': record.driver_id.id,
                                'date_end': reg.date_end,
                                'date': reg.date,
                            }
                        )
                    )
                conductor = record.driver_id.id
            viajes = reg.env['fleet.vehicle.viaje'].search(
                [('liq_driver_id', '=', False), ('driver_id', '!=', False)],
                order="driver_id desc"
            )
            conductor = False
            for record in viajes:
                if record.driver_id.id != conductor:
                    lista.append(
                        (
                            0, 0, {
                                'driver_id': record.driver_id.id,
                                'date_end': reg.date_end,
                                'date': reg.date,
                            }
                        )
                    )
                conductor = record.driver_id.id
            _logger.info('FYI: This is happening %s' % lista)
            reg.update(
                {
                    'driven_liq_det_ids': lista,
                }
            )

    def liquidar_conductores(self):
        for rec in self:
            for rec_driven_liq in self.driven_liq_det_ids:
                inicio = rec_driven_liq.date
                fin = rec_driven_liq.date_end
                lista = [('driver_id', '=', rec_driven_liq.driver_id.id), ('liq_driver_id', '=', False)]
                if inicio:
                    lista.append(('date', '>=', inicio))
                if fin:
                    lista.append(('date', '<=', fin))
                registros = rec_driven_liq.env['fleet.vehicle.viaje'].search(lista)
                inc = 1
                if registros:
                    for record in registros:
                        _logger.info(
                            'FYI: -->record = %s, conductor = %s, interno=%s, cantera=%s liq=%s' %
                            (inc, rec_driven_liq.driver_id.name, record.recibo_interno, record.recibo_cantera, rec.name_seq)
                        )
                        inc += 1
                        record.write({'liq_driver_id': rec.id})
                registros = rec_driven_liq.env['fleet.vehicle.odometer'].search(lista)
                if registros:
                    for record in registros:
                        _logger.info(
                            'FYI: -->record = %s, vehiculo = %s, interno=%s liq=%s' %
                            (inc, rec_driven_liq.driver_id.name, record.recibo, rec.name_seq)
                        )
                        inc += 1
                        record.write({'liq_driver_id': rec.id})
            if rec.driven_liq_det_ids:
                rec.liquidado = True

    def rollback_conductores(self):
        for reg in self:
            _logger.info('FYI: name_sec %s, id=%s' % (reg.name_seq, reg.id))
            registros = reg.env['fleet.vehicle.viaje'].search([('liq_driver_id', '=', reg.id)])
            _logger.info('FYI: registros %s' % (registros))

            if registros:
                for record in registros:
                    record.write({'liq_driver_id': False})
            registros = reg.env['fleet.vehicle.odometer'].search([('liq_driver_id', '=', reg.id)])
            _logger.info('FYI: registros %s' % (registros))
            if registros:
                for record in registros:
                    record.write({'liq_driver_id': False})
            reg.liquidado = False

class employeWorkLiquidacionDetalle(models.Model):
    _name = 'fleet.vehicle.driver.liq.det'
    _description = 'liquidacion de maquinas y viajes de Conductores detalle'

    driver_liq_id = fields.Many2one(
        comodel_name='fleet.vehicle.driver.liq',
        ondelete='restrict'
    )
    driver_id = fields.Many2one(
        comodel_name='res.partner',
        string='Conductor',
        help='Conductor/operador'
    )
    date = fields.Date(
        string='Fecha inicio',
        help="Fecha inicio liquidacion en blanco para inicio de los tiempos"
    )
    date_end = fields.Date(
        string='Fecha fin',
        help="Fecha inicio liquidacion en blanco para fin de los tiempos"
    )
    total_liquidacion = fields.Float(
        string="Total liquidacion"
    )
    nota = fields.Char(
        string="Nota empleado"
    )


class VehicleLiquidacion(models.Model):
    _name = 'fleet.vehicle.liquidacion'
    _description = 'liquidacion de maquinas $$$ por fecha trabajo'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañia',
        default=lambda self: self.env.company,
        ondelete='restrict'
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehículo'
    )
    work_id = fields.Many2one(
        comodel_name='fleet.vehicle.work',
        string='Trabajo'
    )
    liq_id = fields.Many2one(
        comodel_name='fleet.vehicle.work.liq',
        string='Liquidación'
    )
    name_ve = fields.Char(
        string='Vehiculo'
    )
    name_sec_wor = fields.Char(
        string='Consecutivo trabajo'
    )
    name_sec_liq = fields.Char(
        string='Consecutivo liquidación'
    )
    unidades = fields.Float(
        string="unidades a liquidar"
    )
    tipo_unidad = fields.Char(
        string='Tipo unidad'
    )
    precio_unidad = fields.Float(
        string="Precio Unidades"
    )
    valor_unidades = fields.Float(
        string="Valor Unidades"
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id'
    )
