#!/usr/bin/env python3

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.boards.platforms import ulx3s

from litex.soc.cores.clock import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *

from litedram.modules import MT48LC16M16
from litedram.phy import GENSDRPHY


class _CRG(Module):
    def __init__(self, platform):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys_ps = ClockDomain(reset_less=True)

        # # #

        # clk / rst
        clk25 = platform.request("clk25")
        rst = platform.request("rst")

        # pll
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(rst)
        pll.register_clkin(clk25, 25e6)
        pll.create_clkout(self.cd_sys, 50e6, phase=11)
        pll.create_clkout(self.cd_sys_ps, 50e6, phase=20)
        # FIXME: AsyncResetSynchronizer needs FD1S3BX support.
        #self.specials += AsyncResetSynchronizer(self.cd_sys, rst)
        self.comb += self.cd_sys.rst.eq(rst)
        platform.add_period_constraint(self.cd_sys.clk, 20.0)
        platform.add_period_constraint(self.cd_sys_ps.clk, 20.0)

        # sdram clock
        self.comb += platform.request("sdram_clock").eq(self.cd_sys_ps.clk)

        # Stop ESP32 from resetting FPGA
        wifi_gpio0 = platform.request("wifi_gpio0")
        self.comb += wifi_gpio0.eq(1)


class BaseSoC(SoCSDRAM):
    def __init__(self, **kwargs):
        platform = ulx3s.Platform(toolchain="trellis")
        sys_clk_freq = int(50e6)
        SoCSDRAM.__init__(self, platform, clk_freq=sys_clk_freq,
                          integrated_rom_size=0x8000,
                          **kwargs)

        self.submodules.crg = _CRG(platform)

        if not self.integrated_main_ram_size:
            self.submodules.sdrphy = GENSDRPHY(platform.request("sdram"))
            sdram_module = MT48LC16M16(sys_clk_freq, "1:1")
            self.register_sdram(self.sdrphy,
                                sdram_module.geom_settings,
                                sdram_module.timing_settings)

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC port to the ULX3S")
    builder_args(parser)
    soc_sdram_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(**soc_sdram_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build()

if __name__ == "__main__":
    main()
