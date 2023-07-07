import { Hardware } from "@lepton-dashboard/interfaces/hardware";
import { Injectable } from "injection-js";
import hardwareShapes from "../../../infra/definitions/aws_shapes.json";

@Injectable()
export class HardwareService {
  hardwareShapes: Hardware = hardwareShapes as unknown as Hardware;
  isGPUInstance(shape?: string): boolean {
    return this.hardwareShapes && shape
      ? !!this.hardwareShapes[shape].Resource.AcceleratorType
      : false;
  }

  shapes = Object.keys(this.hardwareShapes);
}
