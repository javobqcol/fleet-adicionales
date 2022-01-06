# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class FleetVehicleProductLine(models.Model):
    """Task Line Model."""

    _name = 'fleet.vehicle.product.line'
    _description = 'Linea de producto'

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        fecha = self._context.get('default_date')
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
        if fecha:
            res.update(
                {'date_issued': tz.localize(fields.Datetime.from_string(str(fecha) + ' 00:00:00')).astimezone(pytz.utc)
                 })
        return res

    # task_id = fields.Many2one('service.task',
    #   string='task reference')
    fleet_service_id = fields.Many2one(
        comodel_name='fleet.vehicle.log.services',
        string='Servicio',
        ondelete='restrict'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Producto',
        ondelete='restrict'
    )
    product_name = fields.Char(
        string="Producto",
        required='True'
    )
    qty_hand = fields.Float(
        string='Cantidad en mano',
        help='Cantidad en mano'
    )
    qty = fields.Float(
        string='Usado',
        default=1.0
    )
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string='UOM'
    )
    price_unit = fields.Float(
        string='Costo Unidad'
    )
    total = fields.Float(
        string='Costo total'
    )
    date_issued = fields.Datetime(
        string='Fecha emisión'
    )
    issued_by = fields.Many2one(
        comodel_name='res.users',
        string='Emitido por',
        default=lambda self: self._uid
    )
    is_deliver = fields.Boolean(
        string="Fue entregada?"
    )
    returned = fields.Boolean(
        string="Fue devuelta?"
    )
    note = fields.Char(
        string="Nota"
    )

    @api.constrains('qty', 'qty_hand')
    def _check_used_qty(self):
        for rec in self:
            if rec.qty <= 0:
                raise Warning(
                    _('You can\'t enter used quanity as Zero!')
                )

    @api.onchange('product_id', 'qty')
    def _onchage_product(self):
        for rec in self:
            if rec.product_id:
                prod = rec.product_id
                # if prod.in_active_part:
                #   rec.product_id = False
                #   raise Warning(_('You can\'t select '
                #                   'part which is In-Active!'))
                rec.product_name = "[%s]-%s" % (rec.product_id.code or "", rec.product_id.name) \
                    if not rec.product_name else rec.product_name
                rec.qty_hand = prod.qty_available or 0.0
                rec.product_uom = prod.uom_id or False if not rec.product_uom else rec.product_uom
                rec.price_unit = rec.price_unit if rec.price_unit or rec.price_unit != 0 else prod.list_price or 0.0
            if rec.qty and rec.price_unit:
                rec.total = rec.qty * rec.price_unit

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        for rec in self:
            if rec.qty and rec.price_unit:
                rec.total = rec.qty * rec.price_unit

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', ('product_id.name', operator, name), ('product_name', operator, name)]
        model_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(model_ids).with_user(name_get_uid))

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    _name = 'fleet.vehicle.log.services'
    _order = 'date desc, name_seq desc'

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        service = self.env.ref('fleet-adicionales.type_service_service_8', raise_if_not_found=False)
        # dt = fields.Date.context_today(self)
        dt = False

        res.update({'date': dt, 'cost_subtype_id': service and service.id or False, 'cost_type': 'services'})
        return res

    @api.depends('parts_ids')
    def _compute_get_total(self):
        for rec in self:
            total = 0.0
            rec.sub_total = sum(
                rec.parts_ids.filtered(
                    lambda move: not move.returned
                ).mapped(
                    'total'
                )
            )
            rec.amount = rec.sub_total
            # for line in rec.parts_ids:
            #     total += line.total if not line.returned else 0.0
            # rec.sub_total = total
            # rec.amount = total

    name_seq = fields.Char(
        string='Consecutivo',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    documentos_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='fleet_vehicle_service_attachment_rel',
        column1='service_id',
        column2='attachment_id',
        string='Documentos Servicio'
    )
    parts_ids = fields.One2many(
        comodel_name='fleet.vehicle.product.line',
        inverse_name='fleet_service_id',
        string='Parts'
    )
    sub_total = fields.Float(
        compute="_compute_get_total",
        string='Total de partes',
        store=True
    )

    @api.constrains('date_emp')
    def _check_date(self):
        for record in self:
            if not record.date_emp:
                raise ValidationError("Error, Debe dar un valor de fecha")


    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('fleet-adicionales.service_log.sequence') or _(
                'New')
        result = super(FleetVehicleLogServices, self).create(vals)
        return (result)

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        for rec in self:
            if rec.vehicle_id:
                rec.odometer_unit = rec.vehicle_id.odometer_unit
                rec.driver_id = rec.vehicle_id.driver_id.id

    @api.onchange('inv_ref')
    def _onchange_inv_ref(self):
        res = {}
        for reg in self:
            if reg.inv_ref:
                reg.inv_ref = reg.inv_ref.upper().lstrip()
                hay_recibo = self.search(
                    [('inv_ref', '=', reg.inv_ref),('vendor_id', '=', reg.vendor_id.id),]
                )
                if hay_recibo:
                    warning = {
                        'title': 'Atención:',
                        'message': 'En el sistema hay un recibo de servicio del  proveedor %s con el numero %s'
                                          % (reg.vendor_id.name or "", reg.inv_ref or "")}
                    res.update(
                        {
                            'warning': warning
                        }
                    )
            return res

    def name_get(self):
        res = []
        for field in self:
            res.append(
                (
                    field.id,
                    '%s (%s) [%s]' % (field.name_seq, field.date or "", field.odometer or "")
                )
            )
        return res

    def unlink(self):
        for record in self:
            if record.parts_ids:
                for partes in record.parts_ids:
                    partes.unlink()
            if record.cost_id:
                if record.cost_id.cost_ids:
                    for services in record.cost_id.cost_ids:
                        services.unlink()
                record.cost_id.unlink()
        return super(FleetVehicleLogServices, self).unlink()

