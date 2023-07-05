import Icon from "@ant-design/icons";

import type { CustomIconComponentProps } from "@ant-design/icons/lib/components/Icon";
import { cloneElement, FC, ReactElement, SVGProps } from "react";
import { CarbonIconProps, Cube, Rocket } from "@carbon/icons-react";

const iconGenerator = (svg: SVGProps<SVGSVGElement>) => {
  const component = () => <>{svg}</>;
  return (props: Partial<CustomIconComponentProps>) => (
    <Icon component={component} {...props} />
  );
};

export const LeptonIcon = iconGenerator(
  <svg width="1em" height="1em" viewBox="0 0 85 85">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      fill="#2D9CDB"
      d="M75.9,48.1V36.9c0-2,0-3.1-0.1-3.9c0-0.4-0.1-0.6-0.1-0.7c-0.1-0.3-0.2-0.5-0.4-0.7c-0.1,0-0.2-0.2-0.6-0.4
	c-0.7-0.5-1.6-1-3.3-2l-9.7-5.6c-1.7-1-2.7-1.5-3.4-1.9c-0.4-0.2-0.6-0.3-0.6-0.3c-0.3-0.1-0.6-0.1-0.9,0c-0.1,0-0.3,0.1-0.6,0.3
	c-0.7,0.4-1.7,0.9-3.4,1.9l-9.7,5.6c-1.7,1-2.7,1.5-3.3,2c-0.3,0.2-0.5,0.4-0.6,0.4c-0.2,0.2-0.3,0.5-0.4,0.7c0,0.1,0,0.3-0.1,0.7
	c0,0.8-0.1,1.9-0.1,3.9v11.2c0,2,0,3.1,0.1,3.9c0,0.4,0.1,0.6,0.1,0.7c0.1,0.3,0.2,0.5,0.4,0.7c0.1,0,0.2,0.2,0.6,0.4
	c0.7,0.5,1.6,1,3.3,2l9.7,5.6c1.7,1,2.7,1.5,3.4,1.9c0.4,0.2,0.6,0.3,0.6,0.3c0.3,0.1,0.6,0.1,0.9,0c0.1,0,0.3-0.1,0.6-0.3
	c0.7-0.4,1.7-0.9,3.4-1.9l9.7-5.6c1.7-1,2.7-1.5,3.3-2c0.3-0.2,0.5-0.4,0.6-0.4c0.2-0.2,0.3-0.5,0.4-0.7c0-0.1,0-0.3,0.1-0.7
	C75.9,51.2,75.9,50.1,75.9,48.1z M75.7,52.7C75.7,52.7,75.7,52.7,75.7,52.7C75.7,52.7,75.7,52.7,75.7,52.7z M75.3,53.4
	C75.3,53.4,75.3,53.4,75.3,53.4C75.3,53.4,75.3,53.4,75.3,53.4z M57.7,63.7C57.7,63.7,57.7,63.7,57.7,63.7
	C57.7,63.7,57.7,63.7,57.7,63.7z M56.9,63.7C56.9,63.7,56.9,63.7,56.9,63.7C56.9,63.7,56.9,63.7,56.9,63.7z M39.3,53.4
	C39.3,53.4,39.3,53.4,39.3,53.4C39.3,53.4,39.3,53.4,39.3,53.4z M38.9,52.7C38.9,52.7,38.9,52.7,38.9,52.7
	C38.9,52.7,38.9,52.7,38.9,52.7z M38.9,32.3C38.9,32.3,38.9,32.3,38.9,32.3C38.9,32.3,38.9,32.3,38.9,32.3z M39.3,31.6
	C39.3,31.6,39.3,31.6,39.3,31.6C39.3,31.6,39.3,31.6,39.3,31.6z M56.9,21.4C56.9,21.4,56.9,21.4,56.9,21.4
	C56.9,21.4,56.9,21.4,56.9,21.4z M57.7,21.4C57.7,21.4,57.7,21.4,57.7,21.4C57.7,21.4,57.7,21.4,57.7,21.4z M75.3,31.6
	C75.3,31.6,75.3,31.6,75.3,31.6C75.3,31.6,75.3,31.6,75.3,31.6z M75.7,32.3C75.7,32.3,75.7,32.3,75.7,32.3
	C75.7,32.3,75.7,32.3,75.7,32.3z M81.9,25.6c-1.2-1.3-2.8-2.3-6-4.1l-9.7-5.6C63,14,61.3,13,59.6,12.7c-1.5-0.3-3.1-0.3-4.6,0
	c-1.7,0.4-3.3,1.3-6.6,3.2l-9.7,5.6c-3.2,1.9-4.9,2.8-6,4.1c-1,1.2-1.8,2.5-2.3,4c-0.5,1.7-0.5,3.6-0.5,7.3v11.2
	c0,3.8,0,5.6,0.5,7.3c0.5,1.5,1.3,2.9,2.3,4c1.2,1.3,2.8,2.3,6,4.1l9.7,5.6c3.2,1.9,4.9,2.8,6.6,3.2c1.5,0.3,3.1,0.3,4.6,0
	c1.7-0.4,3.3-1.3,6.6-3.2l9.7-5.6c3.2-1.9,4.9-2.8,6-4.1c1-1.2,1.8-2.5,2.3-4c0.5-1.7,0.5-3.6,0.5-7.3V36.9c0-3.8,0-5.6-0.5-7.3
	C83.7,28.1,82.9,26.7,81.9,25.6z"
    />
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      fill="#2F80ED"
      d="M46.3,48.1V36.9c0-2,0-3.1-0.1-3.9c0-0.4-0.1-0.6-0.1-0.7c-0.1-0.3-0.2-0.5-0.4-0.7c-0.1,0-0.2-0.2-0.6-0.4
	c-0.7-0.5-1.6-1-3.3-2l-9.7-5.6c-1.7-1-2.7-1.5-3.4-1.9c-0.4-0.2-0.6-0.3-0.6-0.3c-0.3-0.1-0.6-0.1-0.9,0c-0.1,0-0.3,0.1-0.6,0.3
	c-0.7,0.4-1.7,0.9-3.4,1.9l-9.7,5.6c-1.7,1-2.7,1.5-3.3,2c-0.3,0.2-0.5,0.4-0.6,0.4c-0.2,0.2-0.3,0.5-0.4,0.7c0,0.1,0,0.3-0.1,0.7
	c0,0.8-0.1,1.9-0.1,3.9v11.2c0,2,0,3.1,0.1,3.9c0,0.4,0.1,0.6,0.1,0.7c0.1,0.3,0.2,0.5,0.4,0.7c0.1,0,0.2,0.2,0.6,0.4
	c0.7,0.5,1.6,1,3.3,2l9.7,5.6c1.7,1,2.7,1.5,3.4,1.9c0.4,0.2,0.6,0.3,0.6,0.3c0.3,0.1,0.6,0.1,0.9,0c0.1,0,0.3-0.1,0.6-0.3
	c0.7-0.4,1.7-0.9,3.4-1.9l9.7-5.6c1.7-1,2.7-1.5,3.3-2c0.3-0.2,0.5-0.4,0.6-0.4c0.2-0.2,0.3-0.5,0.4-0.7c0-0.1,0-0.3,0.1-0.7
	C46.3,51.2,46.3,50.1,46.3,48.1z M52.3,25.6c-1.2-1.3-2.8-2.3-6-4.1l-9.7-5.6C33.4,14,31.8,13,30,12.7c-1.5-0.3-3.1-0.3-4.6,0
	c-1.7,0.4-3.3,1.3-6.6,3.2l-9.7,5.6c-3.2,1.9-4.9,2.8-6,4.1c-1,1.2-1.8,2.5-2.3,4c-0.5,1.7-0.5,3.6-0.5,7.3v11.2
	c0,3.8,0,5.6,0.5,7.3c0.5,1.5,1.3,2.9,2.3,4c1.2,1.3,2.8,2.3,6,4.1l9.7,5.6c3.2,1.9,4.9,2.8,6.6,3.2c1.5,0.3,3.1,0.3,4.6,0
	c1.7-0.4,3.3-1.3,6.6-3.2l9.7-5.6c3.2-1.9,4.9-2.8,6-4.1c1-1.2,1.8-2.5,2.3-4c0.5-1.7,0.5-3.6,0.5-7.3V36.9c0-3.8,0-5.6-0.5-7.3
	C54.2,28.1,53.4,26.7,52.3,25.6z"
    />
    <path
      fill="#2F80ED"
      d="M42.5,55.5c0.2,0.1,0.4,0.3,0.7,0.4l8,4.6c-1.1,0.9-2.6,1.7-4.9,3.1l-3.8,2.2l-3.8-2.2
	c-2.3-1.4-3.8-2.2-4.9-3.1l8-4.6C42.1,55.7,42.3,55.6,42.5,55.5z"
    />
    <path
      fill="#2D9CDB"
      d="M51.2,24.5c-1.1-0.9-2.6-1.7-4.9-3.1l-3.8-2.2l-3.8,2.2c-2.3,1.4-3.8,2.2-4.9,3.1l8,4.6
	c0.2,0.1,0.5,0.3,0.7,0.4c0.2-0.1,0.4-0.3,0.7-0.4L51.2,24.5z"
    />
  </svg>
);

export const LeptonFillIcon = iconGenerator(
  <svg width="1em" height="1em" viewBox="0 0 85 85" fill="currentColor">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M75.9,48.1V36.9c0-2,0-3.1-0.1-3.9c0-0.4-0.1-0.6-0.1-0.7c-0.1-0.3-0.2-0.5-0.4-0.7c-0.1,0-0.2-0.2-0.6-0.4
	c-0.7-0.5-1.6-1-3.3-2l-9.7-5.6c-1.7-1-2.7-1.5-3.4-1.9c-0.4-0.2-0.6-0.3-0.6-0.3c-0.3-0.1-0.6-0.1-0.9,0c-0.1,0-0.3,0.1-0.6,0.3
	c-0.7,0.4-1.7,0.9-3.4,1.9l-9.7,5.6c-1.7,1-2.7,1.5-3.3,2c-0.3,0.2-0.5,0.4-0.6,0.4c-0.2,0.2-0.3,0.5-0.4,0.7c0,0.1,0,0.3-0.1,0.7
	c0,0.8-0.1,1.9-0.1,3.9v11.2c0,2,0,3.1,0.1,3.9c0,0.4,0.1,0.6,0.1,0.7c0.1,0.3,0.2,0.5,0.4,0.7c0.1,0,0.2,0.2,0.6,0.4
	c0.7,0.5,1.6,1,3.3,2l9.7,5.6c1.7,1,2.7,1.5,3.4,1.9c0.4,0.2,0.6,0.3,0.6,0.3c0.3,0.1,0.6,0.1,0.9,0c0.1,0,0.3-0.1,0.6-0.3
	c0.7-0.4,1.7-0.9,3.4-1.9l9.7-5.6c1.7-1,2.7-1.5,3.3-2c0.3-0.2,0.5-0.4,0.6-0.4c0.2-0.2,0.3-0.5,0.4-0.7c0-0.1,0-0.3,0.1-0.7
	C75.9,51.2,75.9,50.1,75.9,48.1z M75.7,52.7C75.7,52.7,75.7,52.7,75.7,52.7C75.7,52.7,75.7,52.7,75.7,52.7z M75.3,53.4
	C75.3,53.4,75.3,53.4,75.3,53.4C75.3,53.4,75.3,53.4,75.3,53.4z M57.7,63.7C57.7,63.7,57.7,63.7,57.7,63.7
	C57.7,63.7,57.7,63.7,57.7,63.7z M56.9,63.7C56.9,63.7,56.9,63.7,56.9,63.7C56.9,63.7,56.9,63.7,56.9,63.7z M39.3,53.4
	C39.3,53.4,39.3,53.4,39.3,53.4C39.3,53.4,39.3,53.4,39.3,53.4z M38.9,52.7C38.9,52.7,38.9,52.7,38.9,52.7
	C38.9,52.7,38.9,52.7,38.9,52.7z M38.9,32.3C38.9,32.3,38.9,32.3,38.9,32.3C38.9,32.3,38.9,32.3,38.9,32.3z M39.3,31.6
	C39.3,31.6,39.3,31.6,39.3,31.6C39.3,31.6,39.3,31.6,39.3,31.6z M56.9,21.4C56.9,21.4,56.9,21.4,56.9,21.4
	C56.9,21.4,56.9,21.4,56.9,21.4z M57.7,21.4C57.7,21.4,57.7,21.4,57.7,21.4C57.7,21.4,57.7,21.4,57.7,21.4z M75.3,31.6
	C75.3,31.6,75.3,31.6,75.3,31.6C75.3,31.6,75.3,31.6,75.3,31.6z M75.7,32.3C75.7,32.3,75.7,32.3,75.7,32.3
	C75.7,32.3,75.7,32.3,75.7,32.3z M81.9,25.6c-1.2-1.3-2.8-2.3-6-4.1l-9.7-5.6C63,14,61.3,13,59.6,12.7c-1.5-0.3-3.1-0.3-4.6,0
	c-1.7,0.4-3.3,1.3-6.6,3.2l-9.7,5.6c-3.2,1.9-4.9,2.8-6,4.1c-1,1.2-1.8,2.5-2.3,4c-0.5,1.7-0.5,3.6-0.5,7.3v11.2
	c0,3.8,0,5.6,0.5,7.3c0.5,1.5,1.3,2.9,2.3,4c1.2,1.3,2.8,2.3,6,4.1l9.7,5.6c3.2,1.9,4.9,2.8,6.6,3.2c1.5,0.3,3.1,0.3,4.6,0
	c1.7-0.4,3.3-1.3,6.6-3.2l9.7-5.6c3.2-1.9,4.9-2.8,6-4.1c1-1.2,1.8-2.5,2.3-4c0.5-1.7,0.5-3.6,0.5-7.3V36.9c0-3.8,0-5.6-0.5-7.3
	C83.7,28.1,82.9,26.7,81.9,25.6z"
    />
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M46.3,48.1V36.9c0-2,0-3.1-0.1-3.9c0-0.4-0.1-0.6-0.1-0.7c-0.1-0.3-0.2-0.5-0.4-0.7c-0.1,0-0.2-0.2-0.6-0.4
	c-0.7-0.5-1.6-1-3.3-2l-9.7-5.6c-1.7-1-2.7-1.5-3.4-1.9c-0.4-0.2-0.6-0.3-0.6-0.3c-0.3-0.1-0.6-0.1-0.9,0c-0.1,0-0.3,0.1-0.6,0.3
	c-0.7,0.4-1.7,0.9-3.4,1.9l-9.7,5.6c-1.7,1-2.7,1.5-3.3,2c-0.3,0.2-0.5,0.4-0.6,0.4c-0.2,0.2-0.3,0.5-0.4,0.7c0,0.1,0,0.3-0.1,0.7
	c0,0.8-0.1,1.9-0.1,3.9v11.2c0,2,0,3.1,0.1,3.9c0,0.4,0.1,0.6,0.1,0.7c0.1,0.3,0.2,0.5,0.4,0.7c0.1,0,0.2,0.2,0.6,0.4
	c0.7,0.5,1.6,1,3.3,2l9.7,5.6c1.7,1,2.7,1.5,3.4,1.9c0.4,0.2,0.6,0.3,0.6,0.3c0.3,0.1,0.6,0.1,0.9,0c0.1,0,0.3-0.1,0.6-0.3
	c0.7-0.4,1.7-0.9,3.4-1.9l9.7-5.6c1.7-1,2.7-1.5,3.3-2c0.3-0.2,0.5-0.4,0.6-0.4c0.2-0.2,0.3-0.5,0.4-0.7c0-0.1,0-0.3,0.1-0.7
	C46.3,51.2,46.3,50.1,46.3,48.1z M52.3,25.6c-1.2-1.3-2.8-2.3-6-4.1l-9.7-5.6C33.4,14,31.8,13,30,12.7c-1.5-0.3-3.1-0.3-4.6,0
	c-1.7,0.4-3.3,1.3-6.6,3.2l-9.7,5.6c-3.2,1.9-4.9,2.8-6,4.1c-1,1.2-1.8,2.5-2.3,4c-0.5,1.7-0.5,3.6-0.5,7.3v11.2
	c0,3.8,0,5.6,0.5,7.3c0.5,1.5,1.3,2.9,2.3,4c1.2,1.3,2.8,2.3,6,4.1l9.7,5.6c3.2,1.9,4.9,2.8,6.6,3.2c1.5,0.3,3.1,0.3,4.6,0
	c1.7-0.4,3.3-1.3,6.6-3.2l9.7-5.6c3.2-1.9,4.9-2.8,6-4.1c1-1.2,1.8-2.5,2.3-4c0.5-1.7,0.5-3.6,0.5-7.3V36.9c0-3.8,0-5.6-0.5-7.3
	C54.2,28.1,53.4,26.7,52.3,25.6z"
    />
    <path
      d="M42.5,55.5c0.2,0.1,0.4,0.3,0.7,0.4l8,4.6c-1.1,0.9-2.6,1.7-4.9,3.1l-3.8,2.2l-3.8-2.2
	c-2.3-1.4-3.8-2.2-4.9-3.1l8-4.6C42.1,55.7,42.3,55.6,42.5,55.5z"
    />
    <path
      d="M51.2,24.5c-1.1-0.9-2.6-1.7-4.9-3.1l-3.8-2.2l-3.8,2.2c-2.3,1.4-3.8,2.2-4.9,3.1l8,4.6
	c0.2,0.1,0.5,0.3,0.7,0.4c0.2-0.1,0.4-0.3,0.7-0.4L51.2,24.5z"
    />
  </svg>
);

export const EqualIcon = iconGenerator(
  <svg width="1em" height="1em" viewBox="0 0 50 50" fill="currentColor">
    <path d="M 9 15 L 9 19 L 41 19 L 41 15 Z M 9 31 L 9 35 L 41 35 L 41 31 Z" />
  </svg>
);
export const PhotonIcon = () => <CarbonIcon icon={<Cube />} />;

export const DeploymentIcon = () => <CarbonIcon icon={<Rocket />} />;

export const CarbonIcon: FC<{ icon: ReactElement<CarbonIconProps> }> = ({
  icon,
}) => {
  const icons = cloneElement(icon, {
    size: "1em",
  } as unknown as CarbonIconProps);
  return (
    <span role="img" className="anticon">
      {icons}
    </span>
  );
};
