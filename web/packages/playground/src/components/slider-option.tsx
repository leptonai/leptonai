import { FC, ReactNode, useMemo } from "react";
import { Slider } from "@lepton/ui/components/slider";
import { Input } from "@lepton/ui/components/input";

export const SliderOption: FC<{
  title: ReactNode;
  step: number;
  max: number;
  min: number;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
  integer?: boolean;
}> = ({
  title,
  value,
  onChange,
  min,
  step,
  max,
  disabled = false,
  integer,
}) => {
  const valueArrayWrap = useMemo(() => [value], [value]);

  const setVal = (v: string) => {
    const val = integer ? parseInt(v) : parseFloat(v);
    if (isNaN(val)) return;
    onChange(Math.max(min, Math.min(max, val)));
  };

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex justify-between items-center space-x-4">
        <div className="grid-0 shrink-0">
          <small className="text-sm font-medium leading-none">{title}</small>
        </div>
        <div className="grid-0 shrink-0">
          <Input
            className="h-6 px-3 py-0 min-w-[80px]"
            type="number"
            max={max}
            min={min}
            step={step}
            value={value}
            disabled={disabled}
            onChange={(e) => setVal(e.target.value)}
          />
        </div>
      </div>
      <Slider
        disabled={disabled}
        value={valueArrayWrap}
        step={step}
        onValueChange={(v) => onChange(v[0])}
        max={max}
        min={min}
      />
    </div>
  );
};
