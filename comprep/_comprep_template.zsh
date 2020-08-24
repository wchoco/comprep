function _{command}() {{
    comprep=( ${{(@f)"$({comp_func})"}} )
    while [ $#comprep -gt 0 ]; do
        num=$comprep[1]; shift comprep
        params=( ${{comprep[@]:0:$num}} ); shift $num comprep
        args=()
        while [ $#params -gt 0 ]; do
            ty=$params[1]; shift params
            n=$params[1]; shift params
            p=( ${{params[@]:0:$n}} ); shift $n params
            case "$ty" in
                choices)
                    args+=( $p )
                ;;
                    description)
                    desc=( $p )
                    args+=( "-d" "desc" )
                ;;
                title)
                    args+=( "-J" $p )
                    args+=( "-x" $p )
                ;;
                prefix)
                    args+=( "-P" $p )
                ;;
                suffix)
                    args+=( "-S" $p )
                ;;
                files)
                    args+=( "-f" )
                ;;
            esac
        done
        compadd $args
    done
}}

compdef _{command} {command}
