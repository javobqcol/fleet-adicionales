# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)

class FleetVehiculeOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'
    _name = 'fleet.vehicle.odometer'
    _order = 'date desc, value desc'

    company_id = fields.Many2one(
        'res.company', 
        'Compañia', 
        default=lambda self: 
        self.env.company
    )
    value = fields.Float(
        string='Inicial',
        help="Odometro Inicial",
        digits=(10, 2), 
        store=True, 
        readonly=False, 
        group_operator="min",
    )
    value_final = fields.Float(
        string='Final', 
        digits=(10, 2), 
        help="Odometro Final", 
        readonly=False, 
        store=True, 
        group_operator="max"
    ) 
    total_unidades = fields.Float(
        string="Total",
        help="Total odometro", 
        digits=(10, 2), 
        compute="_total_horas", 
        group_operator="sum", 
        readonly=False, 
        copy=False, 
        store=True
    ) 
    total_standby = fields.Float(
        string="Total+SB",
        help="Total standby", 
        digits=(10, 2), 
        compute="_total_horas", 
        group_operator="sum", 
        readonly=False, 
        copy=False, 
        store=True
    )
    date = fields.Date(
        string='Fecha',
        default=False
    )
    work_id = fields.Many2one(
        comodel_name='fleet.vehicle.work',
        string='Trabajo',
        ondelete='restrict',
        domain="[('state','=','activo'),('detalle_ids.vehicle_id','=',vehicle_id)]"
    )
    driver_id = fields.Many2one(
        comodel_name='res.partner',
        related=None, 
        string="Conductor",
        ondelete='restrict',
        required=False
    )
    es_standby = fields.Boolean(
        string="Standby", 
        default=False
    )
    tipo_odometro = fields.Char(
        string='Tipo odometro', 
        default='odometer'
    )
    descripcion = fields.Text(
        string='Notas',
        placeholder='Cualquier información pertinente respecto al trabajo realizado',
        copy=False
    )
    recibo = fields.Char(
        string='Recibo', 
        copy=False,
        help="Numero del recibo de la empresa"
    )
    documentos_ids = fields.Many2many( 
        comodel_name='ir.attachment',
        relation='fleet_vehicle_odometer_attachment_rel',
        column1='odometer_id',
        column2='attachment_id',
        string='Recibos',
        copy=False
    )
    odometer_unit = fields.Char(
        string="unidades horometro"
    )
    tiene_adjunto = fields.Boolean(
        compute='_set_adjunto'
    )
    gal = fields.Float(
        string="Galones",
        copy=False
    )
    liq_id = fields.Many2one(
        comodel_name='fleet.vehicle.work.liq',
        string='liquidacion Trabajo',
        ondelete='restrict',
        domain="[('work_id','=',work_id)]",
        copy=False
    )
    liq_driver_id = fields.Many2one(
        comodel_name='fleet.vehicle.driver.liq',
        ondelete='restrict',
        string='liquidacion Conductor',
        copy=False
    )
    motivo = fields.Selection(
        selection=[('propio', 'Propio de la empresa'), ('ajeno', 'Ajeno a la empresa $')],
        string='Motivo',
        default='ajeno',
        help='Motivo de standby',
        required=True
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    license_plate = fields.Char(
        related='vehicle_id.license_plate',
        store=True,
        string='Placa'
    )
    state = fields.Selection(
        selection=[('active', 'Activo'), ('inactive', 'Servicio/taller'), ('available', 'Disponible')],
        string='Estado',
        default='active',
        help='Estado maquinaria',
        required=True
    )


    def copy(self, default=None):
        if default is None:
            default={}
        default['value'] = self.value_final
        default['date'] = fields.Datetime.from_string(self.date) + \
                          relativedelta(days=1 if self.date.strftime("%w") != "6" else 2)

        return super(FleetVehiculeOdometer, self).copy(default)

    def _set_adjunto(self):
        for reg in self:
            reg.tiene_adjunto = True if reg.documentos_ids else False

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        for rec in self:
            if rec.vehicle_id:
                rec.odometer_unit = rec.vehicle_id.odometer_unit
                rec.driver_id = rec.vehicle_id.driver_id.id

    @api.onchange('date')
    def _onchange_date(self):
        for rec in self:
            if rec.date:
                if rec.date > fields.Date.context_today(rec):
                    return {
                        'warning': {
                            'title': 'Error:',
                            'message': 'Fecha es mayor que la fecha actual', },
                            'value': {'date': fields.Date.context_today(rec)},
                    }
                registro = rec.env['fleet.vehicle.odometer'].search([
                    ('vehicle_id', '=', rec.vehicle_id.id),
                    ('tipo_odometro', '=', rec.tipo_odometro),
                    ('date', '<=', rec.date)],
                    order="date desc",
                    limit=1
                )
                rec.value = (registro.value_final or 0)
                if rec.date.strftime("%w") == "0":
                    rec.descripcion = rec.descripcion or "" + "TRABAJO DOMINICAL"

    @api.depends('value', 'value_final', 'total_unidades')
    def _total_horas(self):
        for rec in self:
            det = rec.env['fleet.vehicle.work.det'].search([
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('work_id', '=', rec.work_id.id),
                ('inactivo', '=', False)], 
                limit=1
            )
            if rec.value_final != 0:
                rec.total_unidades = (rec.value_final or 0) - (rec.value or 0)
                rec.total_standby = rec.total_unidades
                if (rec.motivo == 'ajeno') and (rec.total_unidades < det.unidades_standby):
                    rec.total_standby = det.unidades_standby

    @api.onchange('es_standby', 'motivo')
    def _total_standby(self):
        for rec in self:
            det = rec.env['fleet.vehicle.work.det'].search([
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('work_id', '=', rec.work_id.id),
                ('inactivo', '=', False)], limit=1
            )
            rec.total_standby = rec.total_unidades or 0
            if rec.es_standby and rec.motivo == 'ajeno':
                if rec.total_standby <= det.unidades_standby:
                    rec.total_standby = det.unidades_standby

    @api.onchange('work_id')
    def _onchange_work_id(self):
        for reg in self:
            registro = reg.env['fleet.vehicle.work.det'].search([
                ('vehicle_id', '=', reg.vehicle_id.id),
                ('work_id', '=', reg.work_id.id),
                ('inactivo', '=', False)], 
                limit=1
            )
            reg.es_standby = registro.standby

    @api.onchange('recibo')
    def _onchange_inv_ref(self):
        res = {}
        for reg in self:
            if reg.recibo:
                reg.recibo = reg.recibo.upper().lstrip()
                hay_recibo = self.search([
                    ('recibo', '=', reg.recibo),
                    ('work_id', '=', reg.work_id.id),
                ])
                if hay_recibo:
                    warning = {'title': 'Atención:',
                        'message': 'En el sistema hay un recibo interno con el numero %s' % (reg.recibo)}
                    res.update({'warning': warning})
            return res


    @api.constrains('date')
    def _check_date(self):
        for record in self:
            if not record.date: 
                raise ValidationError("Error, Debe dar un valor de fecha")

    @api.constrains('value', 'value_final','date')
    def _check_value_value_final(self):
        for record in self:
            if record.tipo_odometro == 'odometer':
                if not record.value:
                    raise ValidationError(
                        "Error, Debe dar un valor odometro inicial"
                    )
                if not record.value_final:
                    raise ValidationError(
                        "Error, Debe dar un valor odometro final"
                    )
                if record.value_final < record.value:
                    raise ValidationError(
                        "Error, El odometro final no puede ser menor que el odometro inicial"
                    )
            if record.date > fields.Date.context_today(record):
                raise ValidationError("Error, fecha es mayor que fecha actual")
