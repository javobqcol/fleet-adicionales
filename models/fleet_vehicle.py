# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, UserError, Warning
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging

_logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    _description = 'Viajes de los vehiculos'

    responsable_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsable'
    )
    cubicaje = fields.Float(
        string='Cubicaje en M3'
    )
    carga = fields.Float(
        string='Capacidad de carga en Kg'
    )
    multi_images = fields.One2many(
        comodel_name='multi.images2',
        inverse_name='vehicle_id',
        string='Multi Imagenes'
    )
    fleet_attach_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='fleet_vehicle_attachment_rel',
        column1='vehicle_id',
        column2='attachment_id',
        string='Documentos Adjuntos'
    )
    description = fields.Text(
        string='Acerca del vehículo',
        translate=True
    )
    vehicle_type_id = fields.Many2one(
        comodel_name='vehicle.type',
        string='Tipo Vehículo',
        ondelete='restrict',
        required=True
    )
    code = fields.Selection(
        related='vehicle_type_id.code'
    )
    color_id = fields.Many2one(
        comodel_name='vehicle.color',
        string='Color del vehículo',
        ondelete='restrict'
    )
    odometer_unit = fields.Selection(
        selection=[('kilometers', 'Kilometros'), ('miles', 'Millas'), ('hours', 'Horas'), ],
        string='Uniadades odometro',
        default='hours',
        help='Unidades de odometro',
        required=True
    )
    numero_motor = fields.Char(
        string="Número de motor"
    )
    numero_serie = fields.Char(
        string="Numero de serie"
    )
    numero_chasis = fields.Char(
        string="Numero de chasis"
    )
    limitacion_propiedad = fields.Char(
        string="Limitacion propiedad"
    )
    propietario_id = fields.Many2one(
        comodel_name='res.partner',
        string="Propietario"
    )
    restriccion_movilidad = fields.Char(
        string="Restricion movilidad"
    )
    declaracion_importacion = fields.Char(
        string="Declaracion importación"
    )
    licencia_transito = fields.Char(
        string="Licencia de transito"
    )
    blindaje = fields.Char(
        string="Blindaje"
    )
    fecha_importacion = fields.Date(
        string="Fecha importación"
    )
    fecha_matricula = fields.Date(
        string="Fecha matricula"
    )
    fecha_expedicion = fields.Date(
        string="Fecha exp.lic.tto"
    )
    transito_id = fields.Many2one(
        comodel_name='fleet.vehicle.transito',
        string="Organismo de tránsito"
    )
    cilindrada = fields.Float(
        string='Cilindrada en cc'
    )
    peso = fields.Float(
        string="Peso"
    )
    largo = fields.Float(
        string="Largo"
    )
    alto = fields.Float(
        string="Alto"
    )
    ancho = fields.Float(
        string="ancho"
    )
    mtto_cada = fields.Integer(
        string="Mantemimiento cada"
    )
    aviso_a = fields.Integer(
        string="Aviso cada"
    )
    proximo_mtto = fields.Float(
        String="Proximo mtto",
        compute='_get_last_odometer_service',
        readonly=True
    )
    falta_para_mtto = fields.Float(
        String="falta para mtto",
        compute='_get_last_odometer_service',
        readonly=True
    )
    falta = fields.Float(
        string="falta",
        store=False,
        readonly=True
    )
    col = fields.Char(
        compute='_get_last_odometer_service',
        store=False
    )
    odometer_count = fields.Float(
        compute="_compute_count_all",
        string='Odometro'
    )
    servicio_ultimo_mtto = fields.Many2one(
        comodel_name='fleet.vehicle.log.services',
        string="Ultimo mtto preventivo",
        readonly=True,
        compute='_get_last_odometer_service',
        help='Ultimo mantenimiento preventivo'
    )
    odometro_ultimo_mtto = fields.Float(
        string="Ultimo Servicio mantenimiento",
        readonly=True,
        help='Odometro ultimo mantenimiento preventivo',
        compute='_get_last_odometer_service'
    )
    controlar_ids = fields.Many2many(
        comodel_name='fleet.vehicle.template',
        relation='fleet_vehicle_template_rel',
        column1='vehicle_id',
        column2='template_id',
        domain="[('type_id','=',vehicle_type_id)]",
        options="{'no_create':True, 'color_field':'color'}"
    )
    monitor_count = fields.Integer(
        compute="_compute_count_all",
        string="Historia de partes monitoreadas"
    )
    viajes_count = fields.Integer(
        compute="_compute_count_all",
        string="Historia de viajes realizados"
    )
    partes_ids = fields.One2many(
        comodel_name='fleet.vehicle.monitor',
        inverse_name='vehicle_id',
        string="Partes"
    )

    def on_partes_server_action(self):
        registros = self.search([], order="vehicle_type_id")
        _logger.warning("registros %s" % (registros.ids))
        return self.env.ref('fleet-adicionales.report_monitor_part').report_action(registros.ids)

    def action_accept_driver_change(self):
        # vehicles = self.search([('driver_id', 'in', self.mapped('future_driver_id').ids)])
        # vehicles.write({'driver_id': False})
        # un conductor puedr provisionalmente encargarse de otra maquina..
        self._close_driver_history()

        for vehicle in self:
            vehicle.future_driver_id.sudo().write({'plan_to_change_car': False})
            vehicle.driver_id = vehicle.future_driver_id
            vehicle.future_driver_id = False

    def _compute_count_all(self):
        Odometer = self.env['fleet.vehicle.odometer']
        LogFuel = self.env['fleet.vehicle.log.fuel']
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        Cost = self.env['fleet.vehicle.cost']
        LogMonitor = self.env['fleet.vehicle.monitor.log']
        LogViajes = self.env['fleet.vehicle.viaje']
        for record in self:
            record.odometer_count = sum(
                Odometer.search(
                    [('vehicle_id', '=', record.id), ('liq_id', '=', False)]
                ).mapped(
                    'total_unidades'
                )
            )
            record.fuel_logs_count = LogFuel.search_count(
                [('vehicle_id', '=', record.id)]
            )
            record.service_count = LogService.search_count(
                [('vehicle_id', '=', record.id)]
            )
            record.contract_count = LogContract.search_count(
                [('vehicle_id', '=', record.id), ('state', '!=', 'closed')]
            )
            record.cost_count = Cost.search_count(
                [('vehicle_id', '=', record.id), ('parent_id', '=', False)]
            )
            record.history_count = self.env['fleet.vehicle.assignation.log'].search_count(
                [('vehicle_id', '=', record.id)]
            )
            record.monitor_count = LogMonitor.search_count(
                [('vehicle_id', '=', record.id)]
            )
            record.viajes_count = sum(
                LogViajes.search(
                    [('vehicle_id', '=', record.id), ('liq_id', '=', False)]
                ).mapped(
                    'viajes'
                )
            )

    def open_monitor_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Monitor Logs',
            'view_mode': 'tree',
            'res_model': 'fleet.vehicle.monitor.log',
            'domain': [('vehicle_id', '=', self.id)],
        }

    def return_action_to_open_adic(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet-adicionales', xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    def _get_default_state(self):
        state = self.env.ref('fleet-adicionales.type_activo', raise_if_not_found=False)
        return state if state and state.id else False

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search([('vehicle_id', '=', record.id)], limit=1,
                                                           order='value desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value_final
            else:
                record.odometer = record.odometer if record.odometer else 0

    @api.onchange('vin_sn')
    def _cambio_vin_sn(self):
        for reg in self:
            if reg.vin_sn:
                reg.vin_sn = reg.vin_sn.upper()
                if not reg.numero_chasis:
                    reg.numero_chasis = reg.vin_sn.upper()

    @api.onchange('numero_serie')
    def _cambio_serie(self):
        for reg in self:
            if reg.numero_serie:
                reg.numero_serie = reg.numero_serie.upper()

    @api.onchange('numero_motor')
    def _cambio_motor(self):
        for reg in self:
            if reg.numero_motor:
                reg.numero_motor = reg.numero_motor.upper()

    @api.onchange('numero_chasis')
    def _cambio_chasis(self):
        for reg in self:
            if reg.numero_chasis:
                reg.numero_chasis = reg.numero_chasis.upper()

    @api.onchange('vehicle_type_id')
    def _onchange_type(self):
        for rec in self:
            if rec.vehicle_type_id:
                rec.odometer_unit = rec.vehicle_type_id.unidades
                # print("rec.vehicle_type_id.unidades==========", rec.vehicle_type_id.unidades)
                rec.mtto_cada = rec.vehicle_type_id.mtto_cada
                rec.aviso_a = rec.vehicle_type_id.aviso_a
                rec.falta = (rec.mtto_cada or 0) - (rec.aviso_a or 0)

    def _get_last_odometer_service(self):
        self.odometro_ultimo_mtto = False
        self.servicio_ultimo_mtto = False
        self.proximo_mtto = False
        self.falta_para_mtto = False
        service = self.env.ref('fleet-adicionales.type_service_service_1', raise_if_not_found=False)
        for record in self:
            record.odometro_ultimo_mtto = False
            record.servicio_ultimo_mtto = False
            record.proximo_mtto = False
            record.falta_para_mtto = False
            record.col = 'negro'
            reg = record.env['fleet.vehicle.log.services'].search(
                [('vehicle_id', '=', record.id), ('cost_subtype_id', '=', service and service.id or False,)],
                order='date desc',
                limit=1)
            if reg:
                record.servicio_ultimo_mtto = reg.id
                record.odometro_ultimo_mtto = reg.odometer
                record.proximo_mtto = record.odometro_ultimo_mtto + record.mtto_cada
                record.falta_para_mtto = record.proximo_mtto - record.odometer
                if (record.falta_para_mtto < record.falta):
                    record.col = 'amarillo'
                if (record.falta_para_mtto < 0.0):
                    record.col = 'rojo'

    def _set_odometer(self):
        for record in self:
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.odometer, 'date': date, 'vehicle_id': record.id}
                self.env['fleet.vehicle.odometer'].create(data)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res.update({
            'mtto_cada': self.vehicle_type_id.mtto_cada,
            'aviso_a': self.vehicle_type_id.aviso_a,
            'falta': (self.mtto_cada or 0) - (self.aviso_a or 0)
        })
        return res

# refactorizacion de la creacion de partes de maquinaria a vigilar
#    no es perfecto.. pero esta mucho mejor.. no se insertan los registro sino hasta salvar

    @api.onchange('controlar_ids')
    def _cambio_controlar_ids(self):
        for reg in self:
            lista = []
            vehicle_id = reg._origin.id
            _logger.info('FYI: por aqu pase*****************vehicle %s' % vehicle_id)

            for record in reg.controlar_ids:
                monitor = reg.partes_ids.template_id.parent_id.ids
                _logger.info('FYI: por aqu pase******************* %s' % monitor)
                if record.ids[0] not in monitor:
                    temp = record.env['fleet.vehicle.template'].browse(record.ids[0])
                    for template in temp.child_ids:
                        lista.append(
                            (
                                0, 0, {
                                    'template_id': template.id,
                                    'vehicle_id': vehicle_id
                                }
                            )
                        )
                if lista:
                    reg.update(
                        {
                            'partes_ids': lista,
                        }
                    )

    def _asignarMonitor(self, templates_id=False):
        for record in self:
            vehicle_id = record.id
            if templates_id:
                for reg in templates_id:
                    monitor = record.env['fleet.vehicle.monitor'].search([('vehicle_id', '=', vehicle_id)])
                    if reg not in monitor.template_id.parent_id.ids:
                        temp = record.env['fleet.vehicle.template'].browse(reg)
                        for template in temp.child_ids:
                            data = {'template_id': template.id,
                                    'vehicle_id': vehicle_id}
                            monitor.create(data)

    # @api.model
    # def create(self, values):
    #     res = super().create(values)
    #     if 'controlar_ids' in values:
    #         res._asignarMonitor(values['controlar_ids'][0][2])
    #     return res
    #
    # def write(self, values):
    #     if 'controlar_ids' in values:
    #         self._asignarMonitor(values['controlar_ids'][0][2])
    #     return super().write(values)

    def do_enviar_correo(self, correo, cc_todo):
        template_id = self.env.ref('fleet-adicionales.email_template_vehicle_maintenance').id
        template = self.env['mail.template'].browse(template_id)
        if cc_todo:
            template.email_cc = cc_todo
        if correo:
            template.email_to = correo
            template.send_mail(self.id, force_send=True)

    def run_planificador(self):
        """Busca todas las licencias,
           si la fecha de vencimiento es mayor que la fecha actual, pone su estado en inactivo"""
        # sacar los estados posibles de un vehiculo, o esta activo o esta proximo a mtto
        params = self.env['ir.config_parameter'].sudo()
        activo = self.env.ref('fleet-adicionales.type_activo')
        proximo_mtto = self.env.ref('fleet-adicionales.type_proximo_mtto')
        mtto_urgente = self.env.ref('fleet-adicionales.type_mtto_urgente')

        correo_vehicles = params.get_param('fleet-adicionales.resp_vehicles')
        cc_todo = params.get_param('fleet-adicionales.cc_todo')

        vehiculos_activos = self.search([])

        for mtto in vehiculos_activos:
            #  print(mtto.state_id.id!=mtto_urgente.id)
            #  print(mtto.state_id.id, ' ', mtto_urgente.id)
            if (mtto.falta_para_mtto < 0.0) and (mtto.state_id.id != mtto_urgente.id):
                mtto.write({'state_id': mtto_urgente.id})
                mtto.do_enviar_correo(correo_vehicles, cc_todo)
            elif (0.0 < mtto.falta_para_mtto < mtto.falta) and (mtto.state_id.id != proximo_mtto.id):
                mtto.write({'state_id': proximo_mtto.id})
                mtto.do_enviar_correo()


class MultiImages(models.Model):
    _name = "multi.images2"
    _description = 'Multi Imagenes'
    image = fields.Binary(
        string='Images'
    )
    description = fields.Char(
        string='Description'
    )
    title = fields.Char(
        string='title'
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehículo'
    )


class VehicleType(models.Model):
    """Model Vehicle Type."""

    _name = 'vehicle.type'
    _description = 'Vehicle Type'
    code = fields.Selection(
        selection=[('vehiculo', 'Vehículo'), ('maquinaria', 'Maquinaria Amarilla'), ('menor', 'Herramienta menor'), ],
        string='Tipo de maquinaria',
        default='vehiculo',
        help='Tipo de maquinaria',
        required=True
    )
    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )
    unidades = fields.Selection(
        selection=[('kilometers', 'Kilometros'), ('miles', 'Millas'), ('hours', 'Horas'), ],
        string='Uniadades odometro',
        default='hours',
        help='Unidades de odometro',
        required=True
    )
    mtto_cada = fields.Integer(
        string="Mantemimiento a"
    )
    aviso_a = fields.Integer(
        string="Aviso"
    )


class VehicleColor(models.Model):
    """Color Vehicle Type."""

    _name = 'vehicle.color'
    _description = 'Color del vehículo'
    _order = 'name'

    name = fields.Char(
        string='Color',
        required=True
    )


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

class FleetVehicletemplate(models.Model):
    _name = 'fleet.vehicle.template'
    _description = 'base de datos de templates a monitorear'
    _order = "parent_id asc, orden asc"

    name = fields.Char(
        string='Parte monitorear',
        required=True
    )
    type_id = fields.Many2one(
        comodel_name='vehicle.type'
    )
    referencia = fields.Char(
        string='Ref. ubicaciòn'
    )
    orden = fields.Integer(
        string='orden detalle',
        default=1
    )
    parent_id = fields.Many2one(
        comodel_name='fleet.vehicle.template',
        string="Parte de"
    )
    color = fields.Integer()
    active = fields.Boolean(
        string="activo",
        default=True
    )
    child_ids = fields.One2many(
        comodel_name='fleet.vehicle.template',
        inverse_name='parent_id',
        string='Partes',
        domain=[('active', '=', True)]
    )

    def name_get(self):
        res = []
        anterior = ""
        for field in self:
            if field.parent_id:
                res.append(
                    (
                        field.id,
                        '%s [%s]-%s' % (
                            field.parent_id.name or "",
                            str(field.orden).zfill(2) or "",
                            field.name
                        )
                    )
                )
            else:
                res.append(
                    (
                        field.id,
                        '%s' % (
                            field.name
                        )
                    )
                )
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    vehicle_id = fields.Many2one(
        comodel_name="fleet.vehicle"
    )
    date = fields.Date(
        string='Fecha Adquisición',
        default=fields.Date.today
    )
    assign = fields.Boolean(
        string="Asignado",
        default=False
    )
    employee_id = fields.Many2one(
        comodel_name='res.partner',
        string='Empleado',
        tracking=True,
        copy=False
    )
    invisible = fields.Boolean()
    service_id = fields.Many2one(
        comodel_name='fleet.service.type',
        string='Tipo servicio',
        domain="[('category', '=', 'service')]"
    )

    def name_get(self):
        res = []
        trazable = self.env.ref(
            'fleet-adicionales.category_all_trazable',
            raise_if_not_found=False
        )
        for field in self:
            find = self.env['product.product'].search(
                [('id', '=', field.id), ('categ_id', 'child_of', trazable.id)]
            )
            if find:
                res.append(
                    (
                        field.id,
                        '[%s]-(%s)-%s' % (
                            field.default_code or "",
                            field.date or "",
                            field.name
                        )
                    )
                )
            else:
                res.append(
                    (
                        field.id,
                        '[%s]-%s' % (
                            field.default_code or "",
                            field.name
                        )
                    )
                )
        return res

    def _set_invisible(self, vals):
        trazable = self.env.ref(
            'fleet-adicionales.category_all_Trazable_herramienta',
            raise_if_not_found=False
        )
        vals.update(
            {
                'invisible': True
            }
        )
        if 'categ_id' in vals and vals['categ_id']:
            find = self.env['product.category'].search(
                [('id', '=', trazable.id), ('id', 'parent_of', vals['categ_id'])]
            )
            if find:
                vals.update(
                    {
                        'invisible': False
                    }
                )

    @api.model
    def create(self, vals):
        self._set_invisible(vals)
        res = super().create(vals)
        if 'employee_id' in vals and vals['employee_id']:
            res.create_employee_history(
                vals['employee_id']
            )
        return res

    def write(self, vals):
        self._set_invisible(vals)
        if 'employee_id' in vals and vals['employee_id']:
            employee_id = vals['employee_id']
            self.filtered(lambda v: v.employee_id.id != employee_id).create_employee_history(employee_id)
            if employee_id != self.employee_id:
                self._close_employee_history()

        res = super().write(vals)
        return res

    def _close_employee_history(self):
        self.env['product.product.assignation.log'].search(
            [('product_id', 'in', self.ids),
             ('employee_id', 'in', self.mapped('employee_id').ids),
             ('date_end', '=', False)]
        ).write(
            {
                'date_end': fields.Date.today()
            }
        )

    def create_employee_history(self, employee_id):
        for vehicle in self:
            self.env['product.product.assignation.log'].create({
                'product_id': vehicle.id,
                'employee_id': employee_id,
                'date_start': fields.Date.today(),
            })


class FleetVehicleMonitor(models.Model):
    _name = 'fleet.vehicle.monitor'
    _description = 'Productos a monitorear en ciertas partes del automovil'

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string="Vehiculo"
    )
    template_id = fields.Many2one(
        comodel_name='fleet.vehicle.template',
        string='Parte'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Producto",
        default=False,
        track_visivility="always",
        domain="['|', ('vehicle_id','=',vehicle_id),'&',('assign','=',False),('invisible','=',True)]"
    )

    @api.model
    def write(self, vals):
        product_id_new = False
        if 'product_id' in vals:
            if self.product_id:
                self.product_id.assign = False
                self.product_id.vehicle_id = False
            product_id_new = vals['product_id']
            self.env['product.product'].browse(product_id_new).sudo().write(
                {'assign': True, 'vehicle_id': self.vehicle_id.id})

        dt = fields.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_tz = pytz.UTC.localize(datetime.strptime(dt, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(user_tz).strftime(
            DEFAULT_SERVER_DATETIME_FORMAT)
        data = {'vehicle_id': self.vehicle_id.id,
                'template_id': self.template_id.id,
                'product_id_old': self.product_id.id,
                'product_id_new': product_id_new,
                'fecha': date_tz,
                'user_id': self.env.uid}
        self.env['fleet.vehicle.monitor.log'].create(data)
        return super().write(vals)


class FleetVehicleMonitorLog(models.Model):
    _name = 'fleet.vehicle.monitor.log'
    _order = 'fecha desc, vehicle_id, template_id desc'
    _description = 'Historico repuestos'

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string="Vehiculo"
    )
    template_id = fields.Many2one(
        comodel_name='fleet.vehicle.template',
        string='Parte'
    )
    product_id_old = fields.Many2one(
        comodel_name='product.product',
        string='producto anterior'
    )
    product_id_new = fields.Many2one(
        comodel_name='product.product',
        string='producto siguiente'
    )
    fecha = fields.Datetime(
        string='Fecha cambio'
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Usuario responsable",
        default=lambda self: self.env.uid,
        index=True
    )


class Transito(models.Model):
    _name = 'fleet.vehicle.transito'
    _description = 'listado de transito de colombia'

    name = fields.Char(
        string="Organismos de transito"
    )
    jurisdiccion = fields.Selection(
        selection=[('MUNICIPAL', 'Municipal'), ('DEPARTAMENTAL', 'Departamental')],
        string="Tipo"
    )
    categoria = fields.Selection(
        selection=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        string="Categoria"
    )
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        string='Ente',
        required=True,
        ondelete='cascade'
    )


class ProductAssignationLog(models.Model):
    _name = "product.product.assignation.log"
    _description = "Employees history on a product"
    _order = "create_date desc, date_start desc"

    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Producto",
        required=True
    )
    employee_id = fields.Many2one(
        comodel_name='res.partner',
        string="Empleado",
        required=True
    )
    date_start = fields.Date(
        string="Start Date"
    )
    date_end = fields.Date(
        string="End Date"
    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s' % (field.name or "")))
        return res
