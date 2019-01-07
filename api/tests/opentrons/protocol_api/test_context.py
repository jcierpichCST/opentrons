""" Test the functions and classes in the protocol context """

import json
import pkgutil

import opentrons.protocol_api as papi
from opentrons.types import Mount, Point, Location
from opentrons.hardware_control import API, adapters
from opentrons.hardware_control.pipette import Pipette
from opentrons.hardware_control.types import Axis
from opentrons.config.pipette_config import configs

import pytest


@pytest.fixture
def load_my_labware(monkeypatch):
    def dummy_load(labware_name):
        labware_def = json.loads(
            pkgutil.get_data('opentrons',
                             'shared_data/definitions2/{}.json'.format(
                                 labware_name)))
        return labware_def
    monkeypatch.setattr(papi.labware, '_load_definition_by_name', dummy_load)


def test_load_instrument(loop):
    ctx = papi.ProtocolContext(loop=loop)
    for config in configs:
        loaded = ctx.load_instrument(config, Mount.LEFT, replace=True)
        assert loaded.name == config
        prefix = config.split('_v')[0]
        loaded = ctx.load_instrument(prefix, Mount.RIGHT, replace=True)
        assert loaded.name.startswith(prefix)


async def test_motion(loop):
    hardware = API.build_hardware_simulator(loop=loop)
    ctx = papi.ProtocolContext(loop)
    ctx.connect(hardware)
    ctx.home()
    instr = ctx.load_instrument('p10_single', Mount.RIGHT)
    old_pos = await hardware.current_position(instr._mount)
    instr.home()
    assert instr.move_to(Location(Point(0, 0, 0), None)) is instr
    old_pos[Axis.X] = 0
    old_pos[Axis.Y] = 0
    old_pos[Axis.A] = 0
    old_pos[Axis.C] = 2
    assert await hardware.current_position(instr._mount) == old_pos


def test_location_cache(loop, monkeypatch, load_my_labware):
    hardware = API.build_hardware_simulator(loop=loop)
    ctx = papi.ProtocolContext(loop)
    ctx.connect(hardware)
    right = ctx.load_instrument('p10_single', Mount.RIGHT)
    lw = ctx.load_labware_by_name('generic_96_wellPlate_380_uL', 1)
    ctx.home()

    test_args = None

    def fake_plan_move(from_loc, to_loc, deck,
                       well_z_margin=None,
                       lw_z_margin=None):
        nonlocal test_args
        test_args = (from_loc, to_loc, deck, well_z_margin, lw_z_margin)
        return [Point(0, 1, 10), Point(1, 2, 10), Point(1, 2, 3)]

    monkeypatch.setattr(papi.geometry, 'plan_moves', fake_plan_move)
    # When we move without a cache, the from location should be the gantry
    # position
    right.move_to(lw.wells()[0].top())
    # The home position from hardware_control/simulator.py, taking into account
    # that the right pipette is a p10 single which is a different height than
    # the reference p300 single
    assert test_args[0].point == Point(418, 353, 205)
    assert test_args[0].labware is None

    # Once we have a location cache, that should be our from_loc
    right.move_to(lw.wells()[1].top())
    assert test_args[0].labware == lw.wells()[0]


def test_move_uses_arc(loop, monkeypatch, load_my_labware):
    hardware = API.build_hardware_simulator(loop=loop)
    ctx = papi.ProtocolContext(loop)
    ctx.connect(hardware)
    ctx.home()
    right = ctx.load_instrument('p10_single', Mount.RIGHT)
    lw = ctx.load_labware_by_name('generic_96_wellPlate_380_uL', 1)
    ctx.home()

    targets = []

    async def fake_move(mount, target_pos):
        nonlocal targets
        targets.append((mount, target_pos))
    monkeypatch.setattr(hardware, 'move_to', fake_move)

    right.move_to(lw.wells()[0].top())
    assert len(targets) == 3
    assert targets[-1][0] == Mount.RIGHT
    assert targets[-1][1] == lw.wells()[0].top().point


def test_pipette_info(loop):
    ctx = papi.ProtocolContext(loop)
    right = ctx.load_instrument('p300_multi', Mount.RIGHT)
    left = ctx.load_instrument('p1000_single', Mount.LEFT)
    assert right.type == 'multi'
    name = ctx._hw_manager.hardware.attached_instruments[Mount.RIGHT]['name']
    assert right.name == name
    assert left.type == 'single'
    name = ctx._hw_manager.hardware.attached_instruments[Mount.LEFT]['name']
    assert left.name == name


def test_pick_up_and_drop_tip(loop, load_my_labware):
    ctx = papi.ProtocolContext(loop)
    ctx.home()
    tiprack = ctx.load_labware_by_name('opentrons_96_tiprack_300_uL', 1)
    tip_length = tiprack.tip_length
    mount = Mount.LEFT

    instr = ctx.load_instrument('p300_single', mount, tip_racks=[tiprack])

    pipette: Pipette = ctx._hw_manager.hardware._attached_instruments[mount]
    model_offset = Point(*pipette.config.model_offset)
    assert pipette.critical_point() == model_offset
    target_location = tiprack.wells_by_index()['A1'].top()

    instr.pick_up_tip(target_location)

    new_offset = model_offset - Point(0, 0,
                                      tip_length - pipette.config.tip_overlap)
    assert pipette.critical_point() == new_offset

    instr.drop_tip(target_location)
    assert pipette.critical_point() == model_offset


def test_return_tip(loop, load_my_labware):
    ctx = papi.ProtocolContext(loop)
    ctx.home()
    tiprack = ctx.load_labware_by_name('opentrons_96_tiprack_300_uL', 1)
    mount = Mount.LEFT

    instr = ctx.load_instrument('p300_single', mount, tip_racks=[tiprack])

    with pytest.raises(TypeError):
        instr.return_tip()

    pipette: Pipette\
        = ctx._hw_manager.hardware._attached_instruments[mount]

    target_location = tiprack.wells_by_index()['A1'].top()
    instr.pick_up_tip(target_location)

    assert pipette.has_tip

    instr.return_tip()
    assert not pipette.has_tip


def test_pick_up_tip_no_location(loop, load_my_labware):
    ctx = papi.ProtocolContext(loop)
    ctx.home()

    tiprack1 = ctx.load_labware_by_name('opentrons_96_tiprack_300_uL', 1)
    tip_length1 = tiprack1.tip_length

    tiprack2 = ctx.load_labware_by_name('opentrons_96_tiprack_300_uL', 2)
    tip_length2 = tip_length1 + 1.0
    tiprack2.tip_length = tip_length2

    mount = Mount.LEFT

    instr = ctx.load_instrument(
        'p300_single', mount, tip_racks=[tiprack1, tiprack2])

    pipette: Pipette = ctx._hw_manager.hardware._attached_instruments[mount]
    model_offset = Point(*pipette.config.model_offset)
    assert pipette.critical_point() == model_offset

    instr.pick_up_tip()

    assert 'picking up tip' in ','.join([cmd.lower()
                                         for cmd in ctx.commands()])

    new_offset = model_offset - Point(0, 0,
                                      tip_length1 - pipette.config.tip_overlap)
    assert pipette.critical_point() == new_offset

    # TODO: remove argument and verify once trash container is added
    instr.drop_tip(tiprack1.wells()[0].top())
    assert pipette.critical_point() == model_offset

    for well in tiprack1.wells():
        if well.has_tip:
            tiprack1.use_tips(well)

    assert tiprack1.next_tip() is None

    assert tiprack2.wells()[0].has_tip
    instr.pick_up_tip()
    assert not tiprack2.wells()[0].has_tip


def test_instrument_trash(loop, load_my_labware):
    ctx = papi.ProtocolContext(loop)
    ctx.home()

    mount = Mount.LEFT
    instr = ctx.load_instrument('p300_single', mount)

    assert instr.trash_container.name == 'opentrons_1_trash_1.1_L'

    new_trash = ctx.load_labware_by_name('usa_scientific_12_trough_22_mL', 2)
    instr.trash_container = new_trash

    assert instr.trash_container.name == 'usa_scientific_12_trough_22_mL'


def test_aspirate(loop, load_my_labware, monkeypatch):
    ctx = papi.ProtocolContext(loop)
    ctx.home()
    lw = ctx.load_labware_by_name('generic_96_wellPlate_380_uL', 1)
    instr = ctx.load_instrument('p10_single', Mount.RIGHT)

    asp_called_with = None

    async def fake_hw_aspirate(mount, volume=None, rate=1.0):
        nonlocal asp_called_with
        asp_called_with = (mount, volume, rate)

    move_called_with = None

    def fake_move(mount, loc):
        nonlocal move_called_with
        move_called_with = (mount, loc)

    monkeypatch.setattr(ctx._hw_manager.hardware._api,
                        'aspirate', fake_hw_aspirate)
    monkeypatch.setattr(ctx._hw_manager.hardware._api, 'move_to', fake_move)

    instr.aspirate(2.0, lw.wells()[0].bottom())
    assert 'aspirating' in ','.join([cmd.lower() for cmd in ctx.commands()])

    assert asp_called_with == (Mount.RIGHT, 2.0, 1.0)
    assert move_called_with == (Mount.RIGHT, lw.wells()[0].bottom().point)

    instr.well_bottom_clearance = 1.0
    instr.aspirate(2.0, lw.wells()[0])
    dest_point, dest_lw = lw.wells()[0].bottom()
    dest_point = dest_point._replace(z=dest_point.z + 1.0)
    assert move_called_with == (Mount.RIGHT, dest_point)

    move_called_with = None
    instr.aspirate(2.0)
    assert move_called_with is None


def test_dispense(loop, load_my_labware, monkeypatch):
    ctx = papi.ProtocolContext(loop)
    ctx.home()
    lw = ctx.load_labware_by_name('generic_96_wellPlate_380_uL', 1)
    instr = ctx.load_instrument('p10_single', Mount.RIGHT)

    disp_called_with = None

    async def fake_hw_dispense(mount, volume=None, rate=1.0):
        nonlocal disp_called_with
        disp_called_with = (mount, volume, rate)

    move_called_with = None

    def fake_move(mount, loc):
        nonlocal move_called_with
        move_called_with = (mount, loc)

    monkeypatch.setattr(ctx._hw_manager.hardware._api,
                        'dispense', fake_hw_dispense)
    monkeypatch.setattr(ctx._hw_manager.hardware._api, 'move_to', fake_move)

    instr.dispense(2.0, lw.wells()[0].bottom())
    assert 'dispensing' in ','.join([cmd.lower() for cmd in ctx.commands()])
    assert disp_called_with == (Mount.RIGHT, 2.0, 1.0)
    assert move_called_with == (Mount.RIGHT, lw.wells()[0].bottom().point)

    instr.well_bottom_clearance = 1.0
    instr.dispense(2.0, lw.wells()[0])
    dest_point, dest_lw = lw.wells()[0].bottom()
    dest_point = dest_point._replace(z=dest_point.z + 1.0)
    assert move_called_with == (Mount.RIGHT, dest_point)

    move_called_with = None
    instr.dispense(2.0)
    assert move_called_with is None


def test_load_module(loop, monkeypatch):
    ctx = papi.ProtocolContext(loop)
    ctx._hw_manager.hardware._backend._attached_modules = [
        ('mod0', 'tempdeck')]
    ctx.home()
    mod = ctx.load_module('tempdeck', 1)
    assert isinstance(mod, papi.TemperatureModuleContext)


def test_tempdeck(loop, monkeypatch):
    ctx = papi.ProtocolContext(loop)
    ctx._hw_manager.hardware._backend._attached_modules = [
        ('mod0', 'tempdeck')]
    mod = ctx.load_module('tempdeck', 1)
    assert ctx.deck[1] == mod._geometry
    assert mod.target is None
    mod.set_temperature(20)
    assert 'setting temperature' in ','.join([cmd.lower()
                                              for cmd in ctx.commands()])
    mod.wait_for_temp()
    assert mod.target == 20
    assert mod.temperature == 20
    mod.deactivate()
    assert 'deactivating temperature' in ','.join([cmd.lower()
                                                   for cmd in ctx.commands()])
    assert mod.target is None
    mod.set_temperature(0)
    assert mod.target == 0


def test_magdeck(loop, monkeypatch):
    ctx = papi.ProtocolContext(loop)
    ctx._hw_manager.hardware._backend._attached_modules = [('mod0', 'magdeck')]
    mod = ctx.load_module('magdeck', 1)
    assert ctx.deck[1] == mod._geometry
    assert mod.status == 'disengaged'
    with pytest.raises(ValueError):
        mod.engage()
    mod.engage(2)
    assert 'engaging magnetic' in ','.join([cmd.lower()
                                            for cmd in ctx.commands()])
    assert mod.status == 'engaged'
    mod.disengage()
    assert 'disengaging magnetic' in ','.join([cmd.lower()
                                               for cmd in ctx.commands()])
    assert mod.status == 'disengaged'
    mod.calibrate()
    assert 'calibrating magnetic' in ','.join([cmd.lower()
                                               for cmd in ctx.commands()])


def test_module_load_labware(loop, monkeypatch):
    ctx = papi.ProtocolContext(loop)
    labware_name = 'generic_96_wellPlate_380_uL'
    labware_def = json.loads(
        pkgutil.get_data('opentrons',
                         'shared_data/definitions2/{}.json'.format(
                             labware_name)))
    ctx._hw_manager.hardware._backend._attached_modules = [
        ('mod0', 'tempdeck')]
    mod = ctx.load_module('tempdeck', 1)
    assert mod.labware is None
    lw = mod.load_labware_by_name(labware_name)
    lw_offset = Point(labware_def['cornerOffsetFromSlot']['x'],
                      labware_def['cornerOffsetFromSlot']['y'],
                      labware_def['cornerOffsetFromSlot']['z'])
    assert lw._offset == lw_offset + mod._geometry.location.point
    assert lw.name == labware_name
    mod2 = ctx.load_module('tempdeck', 2)
    lw2 = mod2.load_labware_by_name(labware_name)
    assert lw2._offset == lw_offset + mod2._geometry.location.point
    assert lw2.name == labware_name


def test_magdeck_labware_props(loop):
    ctx = papi.ProtocolContext(loop)
    labware_name = 'biorad_96_wellPlate_pcr_200_uL'
    labware_def = json.loads(
        pkgutil.get_data('opentrons',
                         'shared_data/definitions2/{}.json'.format(
                             labware_name)))
    ctx._hw_manager.hardware._backend._attached_modules = [('mod0', 'magdeck')]
    mod = ctx.load_module('magdeck', 1)
    assert mod.labware is None
    mod.load_labware_by_name(labware_name)
    mod.engage()
    lw_offset = labware_def['parameters']['magneticModuleEngageHeight']
    assert mod._module._driver.plate_height == lw_offset
    mod.disengage()
    mod.engage(offset=2)
    assert mod._module._driver.plate_height == lw_offset + 2
    mod.disengage()
    mod.engage(height=3)
    assert mod._module._driver.plate_height == 3
    mod._geometry.reset_labware()
    labware_name = 'generic_96_wellPlate_380_uL'
    mod.load_labware_by_name(labware_name)
    with pytest.raises(ValueError):
        mod.engage()
    with pytest.raises(ValueError):
        mod.engage(offset=1)
    mod.engage(height=2)
    assert mod._module._driver.plate_height == 2


def test_hw_manager(loop):
    # When built without an input it should build its own adapter
    mgr = papi.ProtocolContext.HardwareManager(None)
    assert mgr._is_orig
    adapter = mgr.hardware
    # When "disconnecting" from its own simulator, the adapter should
    # be stopped and a new one created
    assert adapter.is_alive()
    new = mgr.reset_hw()
    assert new is not adapter
    assert not adapter.is_alive()
    # When deleted, the self-created adapter should be stopped
    del mgr
    assert not new.is_alive()
    # When built with a hardware API input it should wrap it but not
    # build its own
    mgr = papi.ProtocolContext.HardwareManager(
        API.build_hardware_simulator(loop=loop))
    assert isinstance(mgr.hardware, adapters.SynchronousAdapter)
    assert not mgr._is_orig
    passed = mgr.hardware
    # When disconnecting from a real external adapter, it should create
    # its own simulator and should _not_ stop the old hardware thread
    new = mgr.reset_hw()
    assert new is not passed
    assert mgr._is_orig
    assert passed.is_alive()
    # When connecting to an adapter it shouldn’t rewrap it
    assert mgr.set_hw(passed) is passed
    # And should kill its old one
    assert not new.is_alive()
    del mgr
    # but not its new one, even if deleted
    assert passed.is_alive()
