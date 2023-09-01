import { Code, Login } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useInject } from "@lepton-libs/di";
import { CodeAPIModal } from "@lepton-libs/gradio/code-api-modal";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Button, Grid } from "antd";
import { FC, useState } from "react";
import { catchError, of } from "rxjs";

export const Api: FC<{
  codes: { language: string; code: string }[];
  name: string;
}> = ({ codes, name }) => {
  const { md } = Grid.useBreakpoint();
  const [open, setOpen] = useState(false);
  const authService = useInject(AuthService);
  const user = useStateFromObservable(
    () => authService.getUser().pipe(catchError(() => of(null))),
    undefined
  );
  if (user) {
    return (
      <>
        <Button
          type="text"
          size="small"
          onClick={() => setOpen(true)}
          icon={<CarbonIcon icon={<Code />} />}
        >
          {md !== false ? "API" : null}
        </Button>
        <CodeAPIModal
          codes={codes}
          open={open}
          setOpen={setOpen}
          title={`Copy API for ${name}`}
        />
      </>
    );
  } else if (user === null) {
    return (
      <Button
        href={`${authService.authServerUrl}/api/auth/logout?next=${location.href}`}
        type="text"
        size="small"
        icon={<CarbonIcon icon={<Login />} />}
      >
        {md !== false ? "Login to get API" : null}
      </Button>
    );
  } else {
    return <></>;
  }
};
