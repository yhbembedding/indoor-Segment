from turtle import forward
import torch
import torch.nn as nn
import torch.nn.functional as F

class SeparableConv2d(nn.Sequential):
    def __init__(
        self,
        in_channels,
        out_channels,
        kernel_size,
        stride=1,
        padding=0,
        dilation=1,
        bias=True,
    ):
        dephtwise_conv = nn.Conv2d(
            in_channels,
            in_channels,
            kernel_size,
            stride=stride,
            padding=padding,
            dilation=dilation,
            groups=in_channels,
            bias=False,
        )
        pointwise_conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=1,
            bias=bias,
        )
        super().__init__(dephtwise_conv, pointwise_conv)
class ASPPConv(nn.Sequential):
    def __init__(self, in_channels, out_channels, dilation):
        super().__init__(
            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=dilation,
                dilation=dilation,
                bias=False,
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
        )


class ASPPSeparableConv(nn.Sequential):
    def __init__(self, in_channels, out_channels, dilation):
        super().__init__(
            SeparableConv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=dilation,
                dilation=dilation,
                bias=False,
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
        )

class ASPPPooling(nn.Sequential):
    def __init__(self, in_channels, out_channels):
        super().__init__(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
        )

    def forward(self, x):
        size = x.shape[-2:]
        for mod in self:
            x = mod(x)
        return F.interpolate(x, size=size, mode="bilinear", align_corners=False)
class ASPP(nn.Module):
    def __init__(self,in_channels,out_channels,atrous_rate,separable=False):
        super(ASPP,self).__init__()
        module_list = []
        module_list.append(
            nn.Sequential(
                nn.Conv2d(in_channels=in_channels,out_channels=out_channels,kernel_size=1,bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU()
            )
        )

        rates1,rates2,rates3 = tuple(atrous_rate)

        ASPPConvModule = ASPPConv if not separable else ASPPSeparableConv
        module_list.append(ASPPConvModule(in_channels=in_channels,out_channels=out_channels,dilation=rates1))
        module_list.append(ASPPConvModule(in_channels=in_channels,out_channels=out_channels,dilation=rates2))
        module_list.append(ASPPConvModule(in_channels=in_channels,out_channels=out_channels,dilation=rates3))
        module_list.append(ASPPPooling(in_channels=in_channels,out_channels=out_channels))
        self.convs = nn.ModuleList(module_list)
        self.conv1x1 = nn.Sequential(
            nn.Conv2d(5*out_channels,out_channels,1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    def forward(self,x):
        res = []
        for conv in self.convs:
            res.append(conv(x))
        x = torch.cat(res,dim=1)
        x = self.conv1x1(x)
        return x
    

class DeepLabV3Decoder(nn.Sequential):
    def __init__(self, in_channels, out_channels=256, atrous_rates=(12, 24, 36)):
        super().__init__(
            ASPP(in_channels, out_channels, atrous_rates),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
        )
        self.out_channels = out_channels

    def forward(self, *features):
        return super().forward(features[-1])
"""
net = DeepLabV3Decoder(3)
net.eval()
x = torch.rand(1,3,224,224)
y = net(x)
print(y.shape)"""