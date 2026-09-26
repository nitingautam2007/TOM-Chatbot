import { forwardRef } from "react";

const VARIANTS = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  danger: "btn-danger",
};

const SIZES = {
  sm: "h-11 px-3 text-xs sm:h-9",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-sm sm:text-base",
};

const Button = forwardRef(function Button(
  { variant = "primary", size = "md", className = "", type = "button", ...props },
  ref,
) {
  const classes = [
    "btn",
    VARIANTS[variant] ?? VARIANTS.primary,
    SIZES[size] ?? SIZES.md,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return <button ref={ref} type={type} className={classes} {...props} />;
});

export default Button;
