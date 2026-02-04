from system.kameleon import VM_IMAGES, is_port_free


def test_vm_ports():
    for name, port in VM_IMAGES.items():
        assert is_port_free(port), f"Port {port} za VM {name} je zaseden"
