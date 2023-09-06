import { FC } from "react";
import { Download, Image } from "@carbon/icons-react";
import { Stopwatch } from "../stopwatch";
import { Button } from "@lepton/ui/components/button";
import { Icons } from "@lepton/ui/components/icons";

export const ImageResult: FC<{
  result: string | null;
  prompt: string;
  error: string | null;
  hasResponse: boolean;
  loading: boolean;
}> = ({ result, prompt, loading, hasResponse, error }) => {
  if (result) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="absolute inset-0 backdrop-blur-[100px] overflow-hidden rounded" />
        <Button
          variant="secondary"
          size="icon"
          className="absolute top-2 right-2 z-20 opacity-50"
          asChild
        >
          <a download href={result} target="_blank" rel="noreferrer">
            <Download className="w-3 h-3" />
          </a>
        </Button>

        <img
          className="z-10 w-auto h-auto max-w-full max-h-full"
          alt={prompt || ""}
          src={result}
        />
      </div>
    );
  }
  return (
    <div className="h-full overflow-hidden rounded text-primary/50 border border-border flex items-center justify-center flex-col">
      {error ? (
        <span className="text-destructive">{error}</span>
      ) : loading ? (
        <>
          <div className="mb-2">
            <Icons.Spinner className="mr-2 h-4 w-4 animate-spin" />
          </div>
          {hasResponse ? (
            <span>Rendering...</span>
          ) : (
            <span>
              Generating... (<Stopwatch start />)
            </span>
          )}
        </>
      ) : (
        <div className="flex flex-1 items-center justify-center flex-col opacity-30 text-primary/50 h-full">
          <Image className="w-40 h-40" />
        </div>
      )}
    </div>
  );
};
