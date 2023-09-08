import { SliderOption } from "../slider-option";
import { FC } from "react";
import { Label } from "@lepton/ui/components/label";
import { Checkbox } from "@lepton/ui/components/checkbox";

export interface SdxlOption {
  width: number; // float (numeric value between 768 and 1024)
  height: number; // float (numeric value between 768 and 1024)
  seed: number; // float (numeric value between 0 and 2147483647)
  steps: number; // float (numeric value between 1 and 50)
  use_refiner: boolean;
  random_seed: boolean;
}
export const Options: FC<{
  value: SdxlOption;
  onChange: (v: SdxlOption) => void;
}> = ({ value, onChange }) => {
  return (
    <div className="flex flex-col space-y-4">
      <SliderOption
        title="Width"
        min={768}
        max={1024}
        step={1}
        integer
        onChange={(width) => onChange({ ...value, width })}
        value={value.width}
      />
      <SliderOption
        title="Height"
        min={768}
        max={1024}
        step={1}
        integer
        onChange={(height) => onChange({ ...value, height })}
        value={value.height}
      />
      <SliderOption
        title="Steps"
        min={1}
        max={50}
        step={1}
        integer
        onChange={(steps) => onChange({ ...value, steps })}
        value={value.steps}
      />

      <SliderOption
        title="Seed"
        min={0}
        max={2147483647}
        step={1}
        integer
        disabled={value.random_seed}
        onChange={(seed) => onChange({ ...value, seed })}
        value={value.seed}
      />
      <div className="flex justify-between">
        <Label htmlFor="random-seed">Random Seed</Label>
        <Checkbox
          id="random-seed"
          checked={value.random_seed}
          onCheckedChange={(state) => {
            onChange({ ...value, random_seed: !!state });
          }}
        />
      </div>
      <div className="flex justify-between">
        <Label htmlFor="use-refiner">Use Refiner</Label>
        <Checkbox
          id="use-refiner"
          checked={value.use_refiner}
          onCheckedChange={(state) => {
            onChange({ ...value, use_refiner: !!state });
          }}
        />
      </div>
    </div>
  );
};
